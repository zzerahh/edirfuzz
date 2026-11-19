#!/usr/bin/env python3
"""Enhanced Directory Fuzzer - CLI and orchestration (Person 4).

Authorized security testing only. See README.md for the Rules of Engagement.
"""
from __future__ import annotations

import argparse
import sys
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from core.reporter import Reporter
from core.scope import (
    LEGAL_BANNER,
    Scope,
    ScopeError,
    confirm_authorization,
    is_default_safe_host,
    is_url_in_scope,
    validate_target,
)

DEFAULT_TARGET = "http://127.0.0.1:5000"
DEFAULT_WORDLIST = "wordlists/common.txt"
DEFAULT_INITIAL_RATE = 5.0
DEFAULT_MAX_RATE = 30.0
DEFAULT_TIMEOUT = 5.0
HARD_MAX_RATE = 100.0 
MAX_WORDLIST_ENTRIES = 100_000

console = Console()

STATUS_STYLE = {
    "FOUND": "green", "REDIRECT": "cyan", "AUTH_REQUIRED": "yellow", "FORBIDDEN": "yellow",
    "RATE_LIMITED": "magenta", "SERVER_ERROR": "red", "ERROR": "red",
}


@dataclass
class ScanConfig:
    """Standard configuration names shared by all team modules."""

    target: str
    wordlist: str
    initial_rate: float
    max_rate: float
    timeout: float
    adaptive: bool
    dry_run: bool
    output_format: str
    output_dir: str = "output"

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dirpulse",
        description="DirPulse: Enhanced Directory Fuzzer with live rate control, "
    "adaptive backoff and scope enforcement.",
        epilog=(
    "examples:\n"
    "  dirpulse --dry-run\n"
    "  dirpulse -t http://127.0.0.1:5000 -w wordlists/common.txt\n"
    "  dirpulse --initial-rate 5 --max-rate 30 --adaptive --format both\n"
    "  dirpulse -t http://192.0.2.10 --allow-host 192.0.2.10   "
    "(needs written permission)\n\n"
    "While a scan runs in a terminal, type a number and press Enter "
    "to change req/s live.\n"
    "Press Ctrl+C at any time to stop safely; a partial report is saved."
),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-t", "--target", default=DEFAULT_TARGET,
                        help=f"base URL to scan (default: {DEFAULT_TARGET})")
    parser.add_argument("-w", "--wordlist", default=DEFAULT_WORDLIST,
                        help=f"path wordlist, one entry per line (default: {DEFAULT_WORDLIST})")
    parser.add_argument("--initial-rate", type=float, default=DEFAULT_INITIAL_RATE, metavar="RPS",
                        help=f"starting requests per second (default: {DEFAULT_INITIAL_RATE:g})")
    parser.add_argument("--max-rate", type=float, default=DEFAULT_MAX_RATE, metavar="RPS",
                        help=f"maximum requests per second (default: {DEFAULT_MAX_RATE:g}, "
                             f"hard cap {HARD_MAX_RATE:g})")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, metavar="SEC",
                        help=f"per-request timeout in seconds (default: {DEFAULT_TIMEOUT:g})")
    parser.add_argument("--adaptive", action="store_true",
                        help="enable adaptive rate control (backs off on latency/429/503/timeouts)")
    parser.add_argument("--dry-run", action="store_true",
                        help="show the planned scan and exit without sending any requests")
    parser.add_argument("--format", dest="output_format", choices=("json", "csv", "both"),
                        default="json", help="report format (default: json)")
    parser.add_argument("-o", "--output-dir", default="output",
                        help="directory for reports (default: output/)")
    parser.add_argument("--allow-host", action="append", default=[], metavar="HOST_OR_CIDR",
                        help="add a host, IP or CIDR (max /16) to the authorized scope; repeatable. "
                             "Only use with written permission.")
    parser.add_argument("--yes", action="store_true",
                        help="skip the typed confirmation (only accepted for default safe targets)")
    return parser


def validate_numbers(args: argparse.Namespace) -> None:
    if args.initial_rate <= 0 or args.max_rate <= 0 or args.timeout <= 0:
        raise ScopeError("--initial-rate, --max-rate and --timeout must be greater than 0.")
    if args.max_rate > HARD_MAX_RATE:
        raise ScopeError(f"--max-rate {args.max_rate:g} exceeds the hard safety cap of {HARD_MAX_RATE:g} req/s.")
    if args.initial_rate > args.max_rate:
        raise ScopeError("--initial-rate cannot be higher than --max-rate.")


def load_wordlist(path: str) -> tuple[list[str], int]:

    wl = Path(path)
    if not wl.is_file():
        raise FileNotFoundError(f"Wordlist not found: {path}")
    seen, paths, skipped = set(), [], 0
    with open(wl, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            word = raw.strip()
            if not word or word.startswith("#"):
                continue
            if ("://" in word or word.startswith("//") or "\\" in word or ".." in word
                    or any(c.isspace() or ord(c) < 32 for c in word) or "@" in word):
                skipped += 1
                continue
            entry = "/" + word.lstrip("/")
            if entry not in seen:
                seen.add(entry)
                paths.append(entry)
            if len(paths) >= MAX_WORDLIST_ENTRIES:
                break
    if not paths:
        raise ValueError("Wordlist contains no usable entries.")
    return paths, skipped


def print_plan(cfg: ScanConfig, base_url: str, paths: list[str], skipped: int, scope: Scope) -> None:
    table = Table(title="Scan plan", show_header=False, title_justify="left")
    table.add_row("Target", escape(base_url))
    table.add_row("Wordlist", f"{escape(cfg.wordlist)} ({len(paths)} paths, {skipped} skipped)")
    table.add_row("Rate", f"start {cfg.initial_rate:g} req/s, max {cfg.max_rate:g} req/s")
    table.add_row("Adaptive control", "on" if cfg.adaptive else "off")
    table.add_row("Timeout", f"{cfg.timeout:g}s")
    table.add_row("Report", f"{cfg.output_format.upper()} in {escape(cfg.output_dir)}/")
    table.add_row("Extra scope", ", ".join(sorted(scope.hosts - Scope.default().hosts)) or "none (safe defaults)")
    table.add_row("Estimated time", f"~{len(paths) / cfg.initial_rate:.1f}s at the starting rate")
    console.print(table)


def print_result(result: dict) -> None:
    label = result.get("classification") or "UNKNOWN"
    if label == "NOT_FOUND":
        return  
    style = STATUS_STYLE.get(label, "white")
    detail = f"-> {escape(str(result['redirect']))}" if result.get("redirect") else ""
    if result.get("error"):
        detail = escape(str(result["error"]))
    console.print(f"[{style}]{label:<13}[/{style}] {result.get('status') or '---'!s:<4} "
                  f"{escape(str(result.get('path'))):<24} {result.get('length') or 0:>7}B  {detail}")


def print_summary(results: list[dict], files: list[Path], partial: bool) -> None:
    counts: dict[str, int] = {}
    for r in results:
        key = r.get("classification") or "UNKNOWN"
        counts[key] = counts.get(key, 0) + 1
    table = Table(title="Partial scan summary" if partial else "Scan summary")
    table.add_column("Classification")
    table.add_column("Count", justify="right")
    for key, n in sorted(counts.items()):
        table.add_row(key, str(n))
    console.print(table)
    for f in files:
        console.print(f"[green]Report saved:[/green] {escape(str(f))}")


def start_rate_listener(scheduler, max_rate: float, stop_event: threading.Event) -> None:
    """Let the operator type a new req/s during a scan (interactive terminals only)."""
    if not sys.stdin or not sys.stdin.isatty():
        return

    def listen() -> None:
        while not stop_event.is_set():
            line = sys.stdin.readline()
            if not line:
                return
            try:
                new_rate = float(line.strip())
            except ValueError:
                console.print("[yellow]Type a number (req/s) to change the rate.[/yellow]")
                continue
            if new_rate <= 0:
                console.print("[yellow]Rate must be greater than 0.[/yellow]")
                continue
            new_rate = min(new_rate, max_rate)
            scheduler.set_rate(new_rate)
            console.print(f"[cyan]Rate changed to {new_rate:g} req/s[/cyan]")

    threading.Thread(target=listen, daemon=True, name="rate-listener").start()


def execute_scan(cfg: ScanConfig, base_url: str, paths: list[str], scope: Scope,
                 stop_event: threading.Event, on_result) -> None:

    try:
        from core.scheduler import RateScheduler
        from core.scanner import Scanner
        adaptive = None
        if cfg.adaptive:
            from core.adaptive import AdaptiveController
            adaptive = AdaptiveController(initial_rate=cfg.initial_rate, max_rate=cfg.max_rate)
    except ImportError as exc:
        raise RuntimeError(f"Core module missing: {exc}. Pull the latest main branch.") from exc

    scheduler = RateScheduler(
        initial_rate=cfg.initial_rate,
        max_rate=cfg.max_rate
    )
    scanner = Scanner(base_url=base_url, scheduler=scheduler, adaptive=adaptive,
                      timeout=cfg.timeout, scope=scope)
    start_rate_listener(scheduler, cfg.max_rate, stop_event)
    scanner.run(paths, on_result=on_result, stop_event=stop_event)


def run(argv=None, input_fn=input) -> int:
    args = build_parser().parse_args(argv)
    cfg = ScanConfig(args.target, args.wordlist, args.initial_rate, args.max_rate, args.timeout,
                     args.adaptive, args.dry_run, args.output_format, args.output_dir)

    console.print(
        Panel(
            "[bold cyan]"
            "  ____  _      ____        _          \n"
            " |  _ \\(_)_ __|  _ \\ _   _| |___  ___ \n"
            " | | | | | '__| |_) | | | | / __|/ _ \\\n"
            " | |_| | | |  |  __/| |_| | \\__ \\  __/\n"
            " |____/|_|_|  |_|    \\__,_|_|___/\\___|\n"
            "[/bold cyan]\n"
            + escape(LEGAL_BANNER),
            border_style="cyan",
            padding=(1, 2),
        )

    )    
    
    try:
        validate_numbers(args)
        scope = Scope.default().extended(args.allow_host)
        base_url = validate_target(cfg.target, scope)
        host = urlsplit(base_url).hostname
        safe_target = is_default_safe_host(host)
        if not confirm_authorization(input_fn, assume_yes=args.yes, safe_target=safe_target):
            console.print("[red]Authorization not confirmed. Exiting without sending any request.[/red]")
            return 1
        paths, skipped = load_wordlist(cfg.wordlist)
    except (ScopeError, FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {escape(str(exc))}")
        return 1

    print_plan(cfg, base_url, paths, skipped, scope)
    if cfg.dry_run:
        console.print("[cyan]Dry run: no requests were sent.[/cyan]")
        return 0

    results: list[dict] = []
    stop_event = threading.Event()
    started = datetime.now(timezone.utc)

    def on_result(result: dict) -> None:
        record = dict(result)
        record["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        redirect = record.get("redirect")
        record["redirect_in_scope"] = None if not redirect else is_url_in_scope(redirect, base_url, scope)
        if redirect and not record["redirect_in_scope"]:
            record["error"] = (record.get("error") or "") + "out-of-scope redirect not followed"
        results.append(record)
        print_result(record)

    interrupted = False
    exit_code = 0
    console.print("[bold]Scan started.[/bold] Ctrl+C = stop safely; type a number + Enter = change req/s.")
    try:
        execute_scan(cfg, base_url, paths, scope, stop_event, on_result)
    except KeyboardInterrupt:
        interrupted = True
        stop_event.set()
        console.print("\n[yellow]Kill switch: stopping, no further requests will be sent.[/yellow]")
    except RuntimeError as exc:
        stop_event.set()
        interrupted, exit_code = True, 1
        console.print(f"[red]Error:[/red] {escape(str(exc))}")
    finally:
        stop_event.set()

    meta = {
        "host": host,
        "target": base_url,
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "wordlist": cfg.wordlist,
        "paths_planned": len(paths),
        "config": {k: v for k, v in asdict(cfg).items() if k not in ("target", "wordlist")},
    }
    try:
        files = Reporter(cfg.output_dir, cfg.output_format).save(results, meta, partial=interrupted)
    except OSError as exc:
        console.print(f"[red]Could not save report:[/red] {escape(str(exc))}")
        return 1
    print_summary(results, files, interrupted)
    return 130 if interrupted and exit_code == 0 else exit_code


def main() -> None:
    try:
        sys.exit(run())
    except KeyboardInterrupt:  
        console.print("\n[yellow]Aborted before scanning. No requests were sent.[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()

"""Local JSON / CSV reporting (Person 4).

Data minimisation: only request metadata is stored. Response bodies, cookies,
headers and credentials are never written. Reports go to output/ by default.
"""
from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

TOOL_NAME = "Enhanced Directory Fuzzer"
TOOL_VERSION = "1.0.0"
REPORT_FIELDS = (
    "timestamp", "path", "url", "status", "length", "response_time",
    "redirect", "redirect_in_scope", "classification", "error",
)
NOTICE = (
    "Metadata only. Response bodies, cookies and credentials are never stored. "
    "Authorized testing only."
)


def _safe_filename_part(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._") or "target"


def _csv_safe(value):
    """Neutralise spreadsheet formula injection (=, +, -, @ at cell start)."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def clean_record(result: dict) -> dict:
    """Keep only whitelisted metadata fields from a scanner result."""
    return {field: result.get(field) for field in REPORT_FIELDS}


def summarize(results: list) -> dict:
    counts = Counter(r.get("classification") or "UNKNOWN" for r in results)
    return {"total_requests": len(results), "by_classification": dict(sorted(counts.items()))}


def _atomic_write(path: Path, writer) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        writer(fh)
    os.replace(tmp, path)  # never leaves a half-written report behind


class Reporter:
    def __init__(self, output_dir: str = "output", output_format: str = "json"):
        if output_format not in ("json", "csv", "both"):
            raise ValueError("output_format must be json, csv or both")
        self.output_dir = Path(output_dir)
        self.output_format = output_format

    def save(self, results: list, meta: dict, partial: bool = False) -> list:
        """Write the report(s) and return their paths."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        records = [clean_record(r) for r in results]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        host = _safe_filename_part(meta.get("host") or "target")
        base = f"scan_{host}_{stamp}" + ("_partial" if partial else "")
        document = {
            "tool": TOOL_NAME,
            "version": TOOL_VERSION,
            "notice": NOTICE,
            "status": "partial" if partial else "complete",
            "scan": {k: v for k, v in meta.items() if k != "host"},
            "summary": summarize(records),
            "results": records,
        }
        written = []
        if self.output_format in ("json", "both"):
            path = self.output_dir / f"{base}.json"
            _atomic_write(path, lambda fh: json.dump(document, fh, indent=2, default=str))
            written.append(path)
        if self.output_format in ("csv", "both"):
            path = self.output_dir / f"{base}.csv"

            def write_csv(fh):
                writer = csv.DictWriter(fh, fieldnames=REPORT_FIELDS)
                writer.writeheader()
                for rec in records:
                    writer.writerow({k: _csv_safe(v) for k, v in rec.items()})

            _atomic_write(path, write_csv)
            written.append(path)
        return written

"""Rate demo function : shows the scheduler changing the request rate during a run.

Run from the project root:
    python -m demo.rate_demo

Next person: replace fake_request() with the real scanner request.
"""
import asyncio
import csv
import sys
import time
from pathlib import Path

# Lets `core` be found when this file is run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.scheduler import RateScheduler, rate_per_window  # noqa: E402

# Each phase is (seconds to run, requests per second)
DEFAULT_PHASES = [(3, 5), (3, 15)]
OUTPUT_FILE = Path("output") / "rate_demo.csv"


async def fake_request():
    """Stand-in for one real HTTP request. Replace with the scanner call."""
    await asyncio.sleep(0.01)


async def run_rate_demo(send_request, phases=DEFAULT_PHASES, max_rate=30):
    """Send requests through the scheduler, changing the rate between phases.

    send_request: an async function that makes ONE request.
    Returns the list of dispatch timestamps.
    """
    scheduler = RateScheduler(initial_rate=phases[0][1], max_rate=max_rate)

    for seconds, rate in phases:
        scheduler.set_rate(rate)
        print(f"Phase: {rate} req/s for {seconds}s")
        phase_end = time.monotonic() + seconds
        while time.monotonic() < phase_end:
            async with scheduler:
                await send_request()

    return scheduler.dispatch_times


def write_csv(timestamps, path=OUTPUT_FILE):
    """Save requests per second to a CSV file with columns: second, requests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = rate_per_window(timestamps, window=1.0)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["second", "requests"])
        for second, count in enumerate(counts):
            writer.writerow([second, count])
    return counts


def print_summary(counts):
    print("second  requests")
    for second, count in enumerate(counts):
        print(f"{second:>6}  {count:>8}")


async def main():
    timestamps = await run_rate_demo(fake_request)
    counts = write_csv(timestamps)
    print_summary(counts)
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
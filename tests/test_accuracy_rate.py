import asyncio

import pytest

from core.scheduler import RateScheduler, rate_per_window, measured_rate

def test_rate_per_window_counts_each_second():
    times = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 2.5]
    assert rate_per_window(times, window=1.0) == [5, 2, 1]


def test_rate_per_window_shows_gaps():
    times = [0.0, 0.5, 3.1]
    assert rate_per_window(times, window=1.0) == [2, 0, 0, 1]


def test_rate_per_window_empty():
    assert rate_per_window([]) == []


def test_measured_rate_from_fixed_timestamps():
    times = [0.0, 0.2, 0.4]          # 2 gaps over 0.4 s = 5 req/s
    assert measured_rate(times) == pytest.approx(5.0)


def test_measured_rate_needs_two_timestamps():
    with pytest.raises(ValueError):
        measured_rate([0.0])


def test_live_scheduler_matches_its_rate():
    async def run():
        s = RateScheduler(initial_rate=10, max_rate=30, max_concurrency=50)
        for _ in range(11):
            async with s:
                pass
        return s.dispatch_times

    times = asyncio.run(run())
    assert 8.0 <= measured_rate(times) <= 12.0
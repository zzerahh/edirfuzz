import asyncio

import pytest

from core.scheduler import RateScheduler


def test_rejects_zero_initial_rate():
    with pytest.raises(ValueError):
        RateScheduler(initial_rate=0)


def test_set_rate_clamps_to_max():
    s = RateScheduler(initial_rate=5, max_rate=30)
    assert s.set_rate(100) == 30
    assert s.rate == 30


def test_set_rate_rejects_non_positive():
    s = RateScheduler(initial_rate=5, max_rate=30)
    with pytest.raises(ValueError):
        s.set_rate(0)


def test_rate_is_respected():
    async def run():
        s = RateScheduler(initial_rate=10, max_rate=30, max_concurrency=50)
        for _ in range(11):          # 11 requests = 10 gaps of 0.1 s
            async with s:
                pass
        return s.dispatch_times

    times = asyncio.run(run())
    elapsed = times[-1] - times[0]
    assert 0.9 <= elapsed <= 1.3


def test_live_rate_change():
    async def run():
        s = RateScheduler(initial_rate=5, max_rate=30, max_concurrency=50)

        async def change_later():
            await asyncio.sleep(0.5)
            s.set_rate(20)

        task = asyncio.create_task(change_later())
        for _ in range(20):
            async with s:
                pass
        await task
        return s.dispatch_times

    times = asyncio.run(run())
    gaps = [b - a for a, b in zip(times, times[1:])]
    assert gaps[0] == pytest.approx(0.2, abs=0.05)    
    assert sum(gaps[-5:]) / 5 < 0.1                   


def test_concurrency_cap():
    async def run():
        s = RateScheduler(initial_rate=30, max_rate=30, max_concurrency=2)
        active = 0
        peak = 0

        async def work():
            nonlocal active, peak
            async with s:
                active += 1
                peak = max(peak, active)
                await asyncio.sleep(0.1)
                active -= 1

        await asyncio.gather(*(work() for _ in range(6)))
        return peak

    assert asyncio.run(run()) == 2
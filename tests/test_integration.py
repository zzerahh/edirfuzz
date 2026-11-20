
import asyncio

from core.adaptive import AdaptiveController
from core.scheduler import RateScheduler
from core.scanner import scan_path


def test_adaptive_scheduler_integration():
    controller = AdaptiveController()
    scheduler = RateScheduler(initial_rate=controller.get_rate())

    assert scheduler.rate == 5.0

    controller.record_response(429, 0.2)
    controller.record_response(429, 0.2)

    scheduler.set_rate(controller.get_rate())

    assert controller.get_rate() == 2.5
    assert scheduler.rate == 2.5


def test_adaptive_scheduler_recovery():
    controller = AdaptiveController(recovery_window=3)
    scheduler = RateScheduler(initial_rate=controller.get_rate())

    for _ in range(3):
        controller.record_response(200, 0.1)

    scheduler.set_rate(controller.get_rate())

    assert controller.get_rate() == 6.0
    assert scheduler.rate == 6.0


def test_scheduler_request_dispatch():
    async def run():
        scheduler = RateScheduler(initial_rate=5)

        for _ in range(3):
            async with scheduler:
                pass

        return scheduler.dispatch_times

    timestamps = asyncio.run(run())

    assert len(timestamps) == 3
    assert timestamps == sorted(timestamps)


def test_full_http_integration():
    async def run():
        controller = AdaptiveController(initial_rate=5)
        scheduler = RateScheduler(initial_rate=controller.get_rate())

        results = []

        for path in ["admin", "login", "random123"]:
            async with scheduler:
                result = await asyncio.to_thread(
                    scan_path,
                    "http://127.0.0.1:5000",
                    path
                )

            results.append(result)

            controller.record_response(
                result["status"],
                result["response_time"]
                if result["response_time"] is not None else 0,
                error=result["error"]
            )

            scheduler.set_rate(controller.get_rate())

        return results, scheduler

    results, scheduler = asyncio.run(run())

    assert [r["status"] for r in results] == [200, 200, 404]
    assert all(r["error"] is None for r in results)
    assert len(scheduler.dispatch_times) == 3

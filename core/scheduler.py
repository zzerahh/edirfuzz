"""Shared request-rate scheduler for the Enhanced Directory Fuzzer.

Every outgoing HTTP request must call `async with scheduler:` first.
This keeps all workers under one global rate limit.
"""
import asyncio
import time


class RateScheduler:
    def __init__(self, initial_rate=5.0, max_rate=30.0, max_concurrency=10):
        if initial_rate <= 0:
            raise ValueError("initial_rate must be greater than 0")
        if max_rate <= 0:
            raise ValueError("max_rate must be greater than 0")

        self._max_rate = float(max_rate)
        self._rate = min(float(initial_rate), self._max_rate)
        self._interval = 1.0 / self._rate      # seconds between requests

        self._next_slot = 0.0                  # time when the next request may go
        self._lock = asyncio.Lock()            # stops two workers reserving the same slot
        self._semaphore = asyncio.Semaphore(max_concurrency)

        # Evidence for the report
        self.dispatch_times = []               # monotonic timestamps of each request
        self.rate_history = [(time.monotonic(), self._rate)]

    @property
    def rate(self):
        return self._rate

    @property
    def max_rate(self):
        return self._max_rate

    def set_rate(self, new_rate):
        """Change the request rate. Works while a scan is running.

        Returns the rate actually used (clamped to max_rate).
        """
        new_rate = float(new_rate)
        if new_rate <= 0:
            raise ValueError("rate must be greater than 0")

        new_rate = min(new_rate, self._max_rate)
        self._rate = new_rate
        self._interval = 1.0 / new_rate
        self.rate_history.append((time.monotonic(), new_rate))
        return new_rate

    async def acquire(self):
        """Wait until this request is allowed to go out."""
        async with self._lock:
            now = time.monotonic()
            if self._next_slot < now:
                # Scheduler has been idle, so start from now
                self._next_slot = now
            wait = self._next_slot - now
            self._next_slot += self._interval  # reserve the next slot for the next caller

        if wait > 0:
            await asyncio.sleep(wait)
        self.dispatch_times.append(time.monotonic())

    async def __aenter__(self):
        await self._semaphore.acquire()        # concurrency cap
        try:
            await self.acquire()               # rate limit
        except BaseException:
            self._semaphore.release()
            raise
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._semaphore.release()
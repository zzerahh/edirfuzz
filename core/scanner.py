import asyncio
import time
import httpx

from core.analyzer import classify_response

def load_wordlist(wordlist_path):
    """
    Load paths from a wordlist file.

    Empty lines and comment lines are ignored.
    """

    paths = []

    with open(wordlist_path, "r", encoding="utf-8") as wordlist:
        for line in wordlist:
            path = line.strip()

            if not path:
                continue

            if path.startswith("#"):
                continue

            paths.append(path)

    return paths

def scan_path(base_url, path, timeout=5.0, client=None):
    """
    Scan a single path and return structured response information.
    """

    url = base_url.rstrip("/") + "/" + path.lstrip("/")

    try:
        start_time = time.perf_counter()

        if client is None:
            response = httpx.get(
                url,
                timeout=timeout,
                follow_redirects=False
            )
    
        else:
            response = client.get(
                url,
                timeout=timeout,
                follow_redirects=False
            )

        response_time = time.perf_counter() - start_time

        redirect = response.headers.get("location")

        return {
            "path": "/" + path.lstrip("/"),
            "url": url,
            "status": response.status_code,
            "length": len(response.content),
            "response_time": round(response_time, 4),
            "redirect": redirect,
            "classification": classify_response(response.status_code),
            "error": None
        }

    except httpx.RequestError as error:
        return {
            "path": "/" + path.lstrip("/"),
            "url": url,
            "status": None,
            "length": 0,
            "response_time": None,
            "redirect": None,
            "classification": classify_response(None),
            "error": str(error)
        }

def scan_wordlist(base_url, wordlist_path, timeout=5.0):
    """
    Scan every path contained in a wordlist.

    Returns a list of structured scan results.
    """

    paths = load_wordlist(wordlist_path)
    results = []

    for path in paths:
        result = scan_path(
            base_url=base_url,
            path=path,
            timeout=timeout
        )

        results.append(result)

    return results

class Scanner:
    """
    Integration wrapper used by the CLI.

    Reuses the existing scan_path() implementation while routing every
    request through the shared RateScheduler.
    """

    def __init__(
        self,
        base_url,
        scheduler,
        adaptive=None,
        timeout=5.0,
        scope=None
    ):
        self.base_url = base_url.rstrip("/")
        self.scheduler = scheduler
        self.adaptive = adaptive
        self.timeout = timeout
        self.scope = scope

    def run(self, paths, on_result=None, stop_event=None):
        """
        Scan the supplied paths while respecting the shared scheduler.
        """
        asyncio.run(
            self._run_async(
                paths,
                on_result=on_result,
                stop_event=stop_event
            )
        )

    async def _run_async(self, paths, on_result=None, stop_event=None):
        from core.scope import is_url_in_scope

        with httpx.Client() as client:
            for path in paths:

                if stop_event is not None and stop_event.is_set():
                    break

                url = (
                    self.base_url.rstrip("/")
                    + "/"
                    + path.lstrip("/")
                )

                if self.scope is not None:
                    if not is_url_in_scope(
                        url,
                        self.base_url,
                        self.scope
                    ):
                        continue

                await self.scheduler.acquire()

                result = await asyncio.to_thread(
                    scan_path,
                    self.base_url,
                    path,
                    self.timeout,
                    client
                )

                if self.adaptive is not None:
                    response_time = result["response_time"]
                    if response_time is None:
                        response_time = 0.0

                    new_rate = self.adaptive.record_response(
                        result["status"],
                        response_time,
                        result["error"]
                    )

                    if new_rate != self.scheduler.rate:
                        old_rate = self.scheduler.rate
                        self.scheduler.set_rate(new_rate)

                        print(
                            f"Adaptive rate changed: "
                            f"{old_rate:g} -> {new_rate:g} req/s"
                        )

                if on_result is not None:
                    on_result(result)
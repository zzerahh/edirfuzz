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
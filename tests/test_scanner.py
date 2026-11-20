import httpx
from core.analyzer import classify_response
from core.scanner import load_wordlist, scan_path


def test_classify_response():
    assert classify_response(200) == "FOUND"
    assert classify_response(301) == "REDIRECT"
    assert classify_response(302) == "REDIRECT"
    assert classify_response(401) == "AUTH_REQUIRED"
    assert classify_response(403) == "FORBIDDEN"
    assert classify_response(404) == "NOT_FOUND"
    assert classify_response(429) == "RATE_LIMITED"
    assert classify_response(500) == "SERVER_ERROR"
    assert classify_response(503) == "SERVER_ERROR"
    assert classify_response(None) == "ERROR"


def test_load_wordlist():
    paths = load_wordlist("wordlists/common.txt")

    assert "admin" in paths
    assert "login" in paths
    assert "secret" in paths
    assert "backup.zip" in paths
    assert len(paths) > 0


def test_scan_existing_path():
    result = scan_path(
        "http://127.0.0.1:5000",
        "admin"
    )

    assert result["path"] == "/admin"
    assert result["status"] == 200
    assert result["classification"] == "FOUND"
    assert result["error"] is None


def test_scan_missing_path():
    result = scan_path(
        "http://127.0.0.1:5000",
        "random123"
    )

    assert result["path"] == "/random123"
    assert result["status"] == 404
    assert result["classification"] == "NOT_FOUND"
    assert result["error"] is None

def test_scan_connection_error():
    result = scan_path(
        "http://127.0.0.1:5999",
        "admin",
        timeout=1.0
    )

    assert result["status"] is None
    assert result["length"] == 0
    assert result["response_time"] is None
    assert result["redirect"] is None
    assert result["classification"] == "ERROR"
    assert result["error"] is not None

def test_scan_with_reusable_client():
    with httpx.Client() as client:
        result = scan_path(
            "http://127.0.0.1:5000",
            "login",
            client=client
        )

    assert result["path"] == "/login"
    assert result["status"] == 200
    assert result["classification"] == "FOUND"
    assert result["error"] is None
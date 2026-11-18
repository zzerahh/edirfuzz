def classify_response(status_code):
    """
    Classify an HTTP response based on its status code.
    """

    if status_code is None:
        return "ERROR"

    if status_code == 200:
        return "FOUND"

    if status_code in (301, 302, 307, 308):
        return "REDIRECT"

    if status_code == 401:
        return "AUTH_REQUIRED"

    if status_code == 403:
        return "FORBIDDEN"

    if status_code == 404:
        return "NOT_FOUND"

    if status_code == 429:
        return "RATE_LIMITED"

    if 500 <= status_code <= 599:
        return "SERVER_ERROR"

    return "OTHER"
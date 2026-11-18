
from collections import deque
from datetime import datetime
from math import isfinite


class AdaptiveController:

    def __init__(self, initial_rate=5, max_rate=30, min_rate=1,
                 window_size=10, latency_threshold=1.0, recovery_window=10):

        if not all(isfinite(x) and x > 0 for x in
                   (initial_rate, max_rate, min_rate)):
            raise ValueError("Rates must be positive")

        if not min_rate <= initial_rate <= max_rate:
            raise ValueError("Invalid rate configuration")

        if not isinstance(window_size, int) or window_size < 2:
            raise ValueError("Invalid window size")

        if not isinstance(recovery_window, int) or recovery_window < 1:
            raise ValueError("Invalid recovery window")

        if not isfinite(latency_threshold) or latency_threshold <= 0:
            raise ValueError("Invalid latency threshold")

        self.current_rate = float(initial_rate)
        self.initial_rate = float(initial_rate)
        self.max_rate = float(max_rate)
        self.min_rate = float(min_rate)

        self.latency_threshold = float(latency_threshold)
        self.response_history = deque(maxlen=window_size)
        self.recovery_window = recovery_window

        self.consecutive_429 = 0
        self.consecutive_503 = 0
        self.consecutive_timeouts = 0
        self.stable_responses = 0

        self.rate_history = []

    def get_rate(self):
        return self.current_rate

    def record_response(self, status_code, response_time, error=None):

        if (not isinstance(response_time, (int, float))
                or not isfinite(response_time)
                or response_time < 0):
            raise ValueError("Invalid response time")

        response = {
            "status": status_code,
            "response_time": float(response_time),
            "error": error
        }

        self.response_history.append(response)
        self._analyze_response(response)

        return self.current_rate

    def _analyze_response(self, response):

        status = response["status"]
        latency = response["response_time"]
        error = response["error"]

        error_text = str(error).lower() if error else ""
        is_timeout = "timeout" in error_text or "timed out" in error_text

        if is_timeout:
            self.consecutive_timeouts += 1
        else:
            self.consecutive_timeouts = 0

        if status == 429:
            self.consecutive_429 += 1
        else:
            self.consecutive_429 = 0

        if status == 503:
            self.consecutive_503 += 1
        else:
            self.consecutive_503 = 0

        if error:
            self.stable_responses = 0

            if self.consecutive_timeouts >= 2:
                self._reduce_rate(0.5, "Repeated timeouts")
                self.consecutive_timeouts = 0

            return

        if status == 429:
            self.stable_responses = 0

            if self.consecutive_429 >= 2:
                self._reduce_rate(0.5, "Repeated HTTP 429")
                self.consecutive_429 = 0

            return

        if status == 503:
            self.stable_responses = 0

            if self.consecutive_503 >= 2:
                self._reduce_rate(0.5, "Repeated HTTP 503")
                self.consecutive_503 = 0

            return

        if latency > self.latency_threshold:
            self.stable_responses = 0
            self._reduce_rate(0.8, "High latency")
            return

        if status is None or status >= 500:
            self.stable_responses = 0
            return

        self.stable_responses += 1

        if self.stable_responses >= self.recovery_window:
            self._increase_rate()
            self.stable_responses = 0

    def _reduce_rate(self, factor, reason):

        old_rate = self.current_rate
        self.current_rate = max(
            self.min_rate,
            self.current_rate * factor
        )

        if self.current_rate != old_rate:
            self._log_rate_change(old_rate, self.current_rate, reason)

    def _increase_rate(self):

        old_rate = self.current_rate
        self.current_rate = min(
            self.max_rate,
            self.current_rate + 1.0
        )

        if self.current_rate != old_rate:
            self._log_rate_change(old_rate, self.current_rate, "Recovery")

    def _log_rate_change(self, old_rate, new_rate, reason):

        self.rate_history.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "old_rate": round(old_rate, 2),
            "new_rate": round(new_rate, 2),
            "reason": reason
        })

    def get_statistics(self):

        history = list(self.response_history)

        if history:
            average_latency = sum(
                item["response_time"] for item in history
            ) / len(history)
        else:
            average_latency = 0.0

        return {
            "current_rate": round(self.current_rate, 2),
            "average_latency": round(average_latency, 3),
            "recent_responses": len(history),
            "rate_changes": len(self.rate_history)
        }

    def reset(self):

        self.current_rate = self.initial_rate
        self.response_history.clear()
        self.rate_history.clear()

        self.consecutive_429 = 0
        self.consecutive_503 = 0
        self.consecutive_timeouts = 0
        self.stable_responses = 0

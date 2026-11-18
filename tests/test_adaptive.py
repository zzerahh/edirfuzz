
import pytest

from core.adaptive import AdaptiveController


def test_initial_rate():
    controller = AdaptiveController()
    assert controller.get_rate() == 5.0


def test_custom_rate():
    controller = AdaptiveController(initial_rate=10, max_rate=30)
    assert controller.get_rate() == 10.0


def test_invalid_initial_rate():
    with pytest.raises(ValueError):
        AdaptiveController(initial_rate=0)


def test_invalid_max_rate():
    with pytest.raises(ValueError):
        AdaptiveController(initial_rate=10, max_rate=5)


def test_rate_decreases_after_errors():
    controller = AdaptiveController()

    controller.record_response(429, 0.2)
    controller.record_response(429, 0.2)

    assert controller.get_rate() < 5.0


def test_rate_stays_within_limit():
    controller = AdaptiveController(initial_rate=5, max_rate=10)

    assert controller.min_rate <= controller.get_rate() <= controller.max_rate

import pytest

from taobao_analytics.metrics import calculate_conversion_rate


def test_conversion_rate_returns_zero_when_denominator_is_zero() -> None:
    assert calculate_conversion_rate(0, 0) == 0.0


def test_conversion_rate_rejects_negative_inputs() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        calculate_conversion_rate(-1, 10)

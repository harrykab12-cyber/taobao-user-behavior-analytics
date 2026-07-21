from __future__ import annotations


def calculate_conversion_rate(numerator: int, denominator: int) -> float:
    if numerator < 0 or denominator < 0:
        raise ValueError("numerator and denominator must be non-negative")
    return 0.0 if denominator == 0 else numerator / denominator

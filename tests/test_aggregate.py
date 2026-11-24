"""Testy pomocných výpočtů agregace."""

import statistics

import pytest

from pipeline.aggregate import median_without
from pipeline.config import size_band


@pytest.mark.parametrize("values", [[1, 2, 3], [1, 2, 3, 4], [5, 5, 7, 9, 100], [0, 0, 0, 1, 2, 3]])
def test_median_without_matches_statistics(values):
    values = sorted(values)
    for k in range(len(values)):
        rest = values[:k] + values[k + 1 :]
        assert median_without(values, k) == statistics.median(rest)


@pytest.mark.parametrize(
    "pop, band",
    [(16, 0), (100, 0), (101, 1), (500, 2), (501, 3), (21642, 8), (100000, 9), (100001, 10), (1397880, 10)],
)
def test_size_band(pop, band):
    assert size_band(pop) == band

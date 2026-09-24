import pytest
from hypothesis import given
from hypothesis import strategies as st
from nullcase_sandbox.stats import Rate, differs, wilson_interval


@st.composite
def counts(draw: st.DrawFn, max_runs: int = 500) -> tuple[int, int]:
    runs = draw(st.integers(min_value=1, max_value=max_runs))
    return draw(st.integers(min_value=0, max_value=runs)), runs


@given(counts())
def test_interval_is_within_unit_range_and_contains_the_estimate(c: tuple[int, int]) -> None:
    failures, runs = c
    low, high = wilson_interval(failures, runs)
    assert 0.0 <= low <= failures / runs <= high <= 1.0


@given(counts())
def test_interval_is_symmetric_under_swapping_passes_and_failures(c: tuple[int, int]) -> None:
    failures, runs = c
    low, high = wilson_interval(failures, runs)
    mirror_low, mirror_high = wilson_interval(runs - failures, runs)
    assert low == pytest.approx(1 - mirror_high, abs=1e-12)
    assert high == pytest.approx(1 - mirror_low, abs=1e-12)


@given(counts(max_runs=100), st.integers(min_value=2, max_value=10))
def test_more_runs_at_the_same_rate_narrow_the_interval(c: tuple[int, int], k: int) -> None:
    failures, runs = c
    low, high = wilson_interval(failures, runs)
    wide_low, wide_high = wilson_interval(failures * k, runs * k)
    assert wide_high - wide_low < high - low


@given(counts(), counts())
def test_differs_is_symmetric(a: tuple[int, int], b: tuple[int, int]) -> None:
    assert differs(Rate(*a), Rate(*b)) == differs(Rate(*b), Rate(*a))


@given(counts())
def test_a_rate_never_differs_from_itself(c: tuple[int, int]) -> None:
    assert not differs(Rate(*c), Rate(*c))


def test_known_values() -> None:
    # 0/20: upper bound is z^2 / (n + z^2).
    assert wilson_interval(0, 20) == (0.0, pytest.approx(0.1611, abs=1e-4))
    assert wilson_interval(10, 20) == (
        pytest.approx(0.2993, abs=1e-4),
        pytest.approx(0.7007, abs=1e-4),
    )
    assert differs(Rate(0, 20), Rate(10, 20))
    assert not differs(Rate(0, 20), Rate(2, 20))


@pytest.mark.parametrize(("failures", "runs"), [(0, 0), (-1, 5), (6, 5)])
def test_rejects_invalid_counts(failures: int, runs: int) -> None:
    with pytest.raises(ValueError):
        wilson_interval(failures, runs)

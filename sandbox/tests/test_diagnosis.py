import random
from typing import get_args

from hypothesis import given
from hypothesis import strategies as st
from nullcase_sandbox.diagnosis import (
    CATEGORY_FOR,
    PerturbationName,
    diagnose,
    flip_eligible,
    flipped,
    is_confirmed_flip,
)
from nullcase_sandbox.stats import Rate, differs

NAMES: tuple[PerturbationName, ...] = get_args(PerturbationName)


@st.composite
def rates(draw: st.DrawFn) -> Rate:
    runs = draw(st.integers(min_value=1, max_value=60))
    return Rate(draw(st.integers(min_value=0, max_value=runs)), runs)


perturbation_maps = st.dictionaries(st.sampled_from(NAMES), rates())


@given(rates(), perturbation_maps)
def test_significant_is_exactly_the_non_overlapping_perturbations(
    baseline: Rate, perturbations: dict[PerturbationName, Rate]
) -> None:
    result = diagnose(baseline, perturbations)
    expected = {name for name, r in perturbations.items() if differs(r, baseline)}
    assert set(result.significant) == expected


@given(rates(), perturbation_maps)
def test_category_comes_from_the_largest_significant_effect(
    baseline: Rate, perturbations: dict[PerturbationName, Rate]
) -> None:
    result = diagnose(baseline, perturbations)
    if not result.significant:
        return
    top = result.significant[0]
    assert result.category == CATEGORY_FOR[top]
    effects = [abs(perturbations[n].rate - baseline.rate) for n in result.significant]
    assert effects == sorted(effects, reverse=True)


@given(rates(), perturbation_maps, st.randoms())
def test_result_does_not_depend_on_perturbation_order(
    baseline: Rate, perturbations: dict[PerturbationName, Rate], rnd: random.Random
) -> None:
    items = list(perturbations.items())
    rnd.shuffle(items)
    assert diagnose(baseline, dict(items)) == diagnose(baseline, perturbations)


@given(rates(), st.lists(st.sampled_from(NAMES), unique=True))
def test_perturbations_matching_baseline_fall_back_to_baseline_verdict(
    baseline: Rate, names: list[PerturbationName]
) -> None:
    result = diagnose(baseline, dict.fromkeys(names, baseline))
    assert result.significant == ()
    if baseline.failures == 0:
        assert result.category == "not_reproduced"
    elif baseline.failures == baseline.runs:
        assert result.category == "fails_consistently"
    else:
        assert result.category == "timing"


def test_order_shuffle_that_raises_failures_is_order_dependent() -> None:
    result = diagnose(Rate(0, 20), {"order": Rate(11, 20), "hash_seed": Rate(1, 20)})
    assert result.category == "order_dependent"
    assert result.significant == ("order",)


@given(rates(), st.integers(min_value=1, max_value=10), st.data())
def test_flip_requires_a_constant_baseline_and_unanimous_opposite_replays(
    baseline: Rate, replay_runs: int, data: st.DataObject
) -> None:
    replay_failures = data.draw(st.integers(min_value=0, max_value=replay_runs))
    confirmed = is_confirmed_flip(baseline, replay_failures, replay_runs)
    if 0 < baseline.failures < baseline.runs:
        assert not confirmed
    elif baseline.failures == 0:
        assert confirmed == (replay_failures == replay_runs)
    else:
        assert confirmed == (replay_failures == 0)


@given(rates(), perturbation_maps)
def test_flip_check_only_applies_when_wilson_found_nothing_and_baseline_is_constant(
    baseline: Rate, perturbations: dict[PerturbationName, Rate]
) -> None:
    result = diagnose(baseline, perturbations)
    constant = baseline.failures in (0, baseline.runs)
    assert flip_eligible(result) == (not result.significant and constant)


def test_hash_order_miss_pattern_is_not_significant_by_interval() -> None:
    # The demo repo's hash-order numbers: interval rule alone can't separate them.
    result = diagnose(Rate(20, 20), {"hash_seed": Rate(15, 20)})
    assert result.category == "fails_consistently"
    assert flip_eligible(result)
    assert flipped("hash_seed", "PYTHONHASHSEED=7").category == "hash_order"

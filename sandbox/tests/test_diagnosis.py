import random
from typing import get_args

from hypothesis import given
from hypothesis import strategies as st
from nullcase_sandbox.diagnosis import CATEGORY_FOR, PerturbationName, diagnose
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

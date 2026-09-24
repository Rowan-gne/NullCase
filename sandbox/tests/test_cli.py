import argparse

import pytest
from nullcase_sandbox.cli import perturbation_list


def test_only_accepts_a_comma_separated_list_in_canonical_order() -> None:
    assert perturbation_list("hash_seed, order") == ["order", "hash_seed"]


@pytest.mark.parametrize("value", ["", "order,bogus", "tests/test_x.py::test_y"])
def test_only_rejects_unknown_names(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        perturbation_list(value)

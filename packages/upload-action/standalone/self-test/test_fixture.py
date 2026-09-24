import pytest


def test_passes():
    assert True


@pytest.mark.skip(reason="fixture")
def test_skipped():
    pass

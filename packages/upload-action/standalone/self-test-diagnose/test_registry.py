"""An order-dependent test: passes in file order, fails when another test runs first."""

_registry: list[str] = []


def register(name: str) -> int:
    _registry.append(name)
    return len(_registry)


def test_first_registration_gets_id_1():
    assert register("victim") == 1


def test_polluter_a():
    register("a")


def test_polluter_b():
    register("b")


def test_polluter_c():
    register("c")

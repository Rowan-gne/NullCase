from demo_service.registry import count, register


def test_first_user_gets_id_1():
    assert register("alice") == 1


def test_register_another_user():
    register("bob")
    assert count() >= 1

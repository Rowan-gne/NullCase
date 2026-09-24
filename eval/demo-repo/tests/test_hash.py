from demo_service.tags import unique_tags


def test_unique_tags_keeps_first_seen_order():
    assert unique_tags(["red", "green", "red", "blue"]) == ["red", "green", "blue"]

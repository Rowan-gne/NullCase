from demo_service.http_client import fetch_status


def test_example_dot_com_is_up():
    assert fetch_status("https://example.com") == 200

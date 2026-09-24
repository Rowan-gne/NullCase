"""In-memory user registry."""

_users: list[str] = []


def register(name: str) -> int:
    """Register a user and return their numeric ID."""
    _users.append(name)
    return len(_users)


def count() -> int:
    return len(_users)

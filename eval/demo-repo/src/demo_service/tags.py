"""Tag normalisation."""


def unique_tags(tags: list[str]) -> list[str]:
    """Drop duplicate tags."""
    return list(set(tags))

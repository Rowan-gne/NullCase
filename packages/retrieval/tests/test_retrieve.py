from pathlib import Path

import pytest
from nullcase_retrieval.retrieve import (
    embedding_candidates,
    find_example_tests,
    import_graph_candidates,
    parse_target,
    similarity,
)

# This repository is the fixture: real modules with real tests.
REPO_ROOT = Path(__file__).resolve().parents[3]


def paths(root: Path, target: str) -> list[str]:
    return [c.path.as_posix() for c in import_graph_candidates(root, target)]


# These use the repository's own, growing test suite, so they check that the
# right tests are found and the best match ranks first, not the complete list.


def test_finds_and_ranks_tests_for_a_module_in_this_repo() -> None:
    found = import_graph_candidates(REPO_ROOT, "nullcase_sandbox.stats")
    names = [c.path.as_posix() for c in found]
    assert names[0] == "sandbox/tests/test_stats.py"
    assert "sandbox/tests/test_diagnosis.py" in names
    assert [c.score for c in found] == sorted((c.score for c in found), reverse=True)
    assert all(n.startswith("sandbox/tests/") for n in names)


def test_finds_the_plugin_package_tests_in_this_repo() -> None:
    package = paths(REPO_ROOT, "nullcase_pytest")
    assert {
        "packages/pytest-plugin/tests/test_package.py",
        "packages/pytest-plugin/tests/test_sinks.py",
    } <= set(package)
    assert paths(REPO_ROOT, "nullcase_pytest.sinks")[0] == (
        "packages/pytest-plugin/tests/test_sinks.py"
    )


def test_accepts_a_file_path_and_function_target() -> None:
    target = "sandbox/src/nullcase_sandbox/diagnosis.py:diagnose"
    assert parse_target(REPO_ROOT, target) == ("nullcase_sandbox.diagnosis", "diagnose")
    assert paths(REPO_ROOT, target)[0] == "sandbox/tests/test_diagnosis.py"


def test_module_with_no_importing_tests_falls_through_to_the_embedding_stub() -> None:
    # test_plugin.py exercises the plugin through pytester and never imports it.
    assert paths(REPO_ROOT, "nullcase_pytest.plugin") == []
    with pytest.raises(NotImplementedError, match=r"§3\.9"):
        find_example_tests(REPO_ROOT, "nullcase_pytest.plugin")


def test_returns_top_k_when_enough_candidates() -> None:
    found = find_example_tests(REPO_ROOT, "nullcase_sandbox.stats", k=2)
    assert len(found) == 2
    assert found[0].path.name == "test_stats.py"
    assert found[0].score > found[1].score


def test_too_few_candidates_for_k_falls_through() -> None:
    with pytest.raises(NotImplementedError):
        find_example_tests(REPO_ROOT, "nullcase_sandbox.stats", k=1000)


def test_embedding_stub_raises() -> None:
    with pytest.raises(NotImplementedError):
        embedding_candidates(REPO_ROOT, "anything", k=1)


def test_similarity_prefers_matching_path_tokens() -> None:
    near = similarity("app.billing", None, Path("tests/test_billing.py"))
    far = similarity("app.billing", None, Path("tests/test_users.py"))
    assert near > far

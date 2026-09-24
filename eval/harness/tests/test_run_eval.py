from run_eval import DEMO_REPO, load_labels, score


def test_score_counts_exact_matches_only() -> None:
    labels = {"a": "timing", "b": "network", "c": "order_dependent"}
    predictions = {"a": "timing", "b": "not_reproduced"}
    assert score(predictions, labels) == 1


def test_every_label_names_a_test_file_in_the_demo_repo() -> None:
    labels = load_labels()
    assert len(labels) == 6
    assert len(set(labels.values())) == 6
    for nodeid in labels:
        assert (DEMO_REPO / nodeid.split("::")[0]).is_file()

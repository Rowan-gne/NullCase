import json
from pathlib import Path

import pytest
from nullcase_pytest.quarantine import fetch_quarantine_list
from nullcase_pytest.results import ResultRecord
from nullcase_pytest.sinks import LocalFileSink, RemoteUploadSink

RECORD = ResultRecord(
    nodeid="tests/test_a.py::test_x", file_path="tests/test_a.py", outcome="passed", duration_s=0.5
)


def test_local_file_sink_writes_one_json_line_per_record(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "results.jsonl"
    sink = LocalFileSink(path)
    sink.write(RECORD)
    sink.write(RECORD)
    sink.close()

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {
        "nodeid": "tests/test_a.py::test_x",
        "file_path": "tests/test_a.py",
        "outcome": "passed",
        "duration_s": 0.5,
    }


def test_local_file_sink_truncates_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "results.jsonl"
    path.write_text("stale\n", encoding="utf-8")
    LocalFileSink(path).close()
    assert path.read_text(encoding="utf-8") == ""


def test_remote_upload_sink_is_not_implemented() -> None:
    sink = RemoteUploadSink()
    with pytest.raises(NotImplementedError):
        sink.write(RECORD)
    with pytest.raises(NotImplementedError):
        sink.close()


def test_quarantine_list_stub_is_empty() -> None:
    assert fetch_quarantine_list() == []

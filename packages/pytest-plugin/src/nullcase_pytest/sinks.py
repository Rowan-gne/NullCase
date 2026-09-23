"""Destinations for result records."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from nullcase_pytest.results import ResultRecord


class ResultsSink(ABC):
    """Receives one record per test, then is closed once at session end."""

    @abstractmethod
    def write(self, record: ResultRecord) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


class LocalFileSink(ResultsSink):
    """Writes records to a local file as JSON Lines, one record per line.

    The file is truncated when the sink is created and flushed after every
    record, so a crashed session still leaves the results gathered so far.
    """

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._file = path.open("w", encoding="utf-8")

    def write(self, record: ResultRecord) -> None:
        self._file.write(record.to_json() + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()


class RemoteUploadSink(ResultsSink):
    """Uploads results to the NullCase API. Not implemented.

    Planned design (docs/technical-guide.md §3.5): inside GitHub Actions the
    plugin requests an OIDC token with audience ``nullcase`` (the workflow
    grants ``permissions: id-token: write``) and uploads the results with it;
    the API verifies the token's signature, issuer, audience and
    ``repository`` claim. Fork PRs receive no OIDC token, so upload is skipped
    silently there. No backend exists yet, so this sink only raises.
    """

    def write(self, record: ResultRecord) -> None:
        raise NotImplementedError("Remote upload is not implemented yet; use LocalFileSink.")

    def close(self) -> None:
        raise NotImplementedError("Remote upload is not implemented yet; use LocalFileSink.")

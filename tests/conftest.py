import os
import subprocess
from pathlib import Path

import pytest


class RepoBuilder:
    """A throwaway git repo with deterministic authors and dates."""

    def __init__(self, path: Path):
        self.path = path
        path.mkdir(parents=True)
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.name", "Ana")
        self._git("config", "user.email", "ana@example.com")
        self._git("config", "commit.gpgsign", "false")

    def _git(self, *args: str, env: dict | None = None) -> str:
        out = subprocess.run(
            ["git", *args], cwd=self.path, check=True, capture_output=True,
            env={**os.environ, **(env or {})},
        )
        return out.stdout.decode()

    def write(self, path: str, text: str | bytes) -> None:
        f = self.path / path
        f.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            f.write_bytes(text)
        else:
            f.write_text(text, encoding="utf-8")
        self._git("add", "--", path)

    def delete(self, path: str) -> None:
        self._git("rm", "-q", "--", path)

    def rename(self, old: str, new: str) -> None:
        (self.path / new).parent.mkdir(parents=True, exist_ok=True)
        self._git("mv", "--", old, new)

    def commit(self, msg: str, author: str = "Ana <ana@example.com>",
               date: str = "2020-01-01T12:00:00+00:00") -> str:
        env = {"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
        self._git("commit", "-q", "--allow-empty", "-m", msg, f"--author={author}", env=env)
        return self._git("rev-parse", "HEAD").strip()


@pytest.fixture
def repo(tmp_path) -> RepoBuilder:
    return RepoBuilder(tmp_path / "r")

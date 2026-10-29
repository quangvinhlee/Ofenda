"""Read a repository's whole history in one `git log` pass."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .git import GitError, run_git

_FORMAT = "%x1e%H%x1f%aN%x1f%aE%x1f%aI%x1f%s"


@dataclass(frozen=True)
class Commit:
    sha: str
    author: str
    email: str
    date: datetime
    subject: str


@dataclass(frozen=True)
class Change:
    status: str  # first letter only: A, C, D, M, R, T
    old_blob: str
    new_blob: str
    path: str
    old_path: str | None


@dataclass(frozen=True)
class Entry:
    commit: Commit
    changes: tuple[Change, ...]


def read_history(repo: Path) -> list[Entry]:
    """Every commit, oldest first, with its raw file changes."""
    try:
        run_git(repo, "rev-parse", "--verify", "-q", "HEAD")
    except GitError:
        run_git(repo, "rev-parse", "--git-dir")  # raises if this is not a repo at all
        return []
    out = run_git(
        repo, "log", "-z", "--reverse", "--date-order", "--raw", "--no-abbrev",
        "-M", "--use-mailmap", f"--format={_FORMAT}",
    )
    return [_parse_chunk(chunk) for chunk in out.split("\x1e")[1:]]


def _parse_chunk(chunk: str) -> Entry:
    header, _, rest = chunk.partition("\x00")
    sha, author, email, date, subject = header.split("\x1f", 4)
    commit = Commit(sha, author, email, datetime.fromisoformat(date), subject.strip())

    tokens = rest.lstrip("\n").split("\x00")
    changes: list[Change] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        i += 1
        if not tok.startswith(":"):
            continue
        _old_mode, _new_mode, old_blob, new_blob, status = tok[1:].split(" ")
        kind = status[0]
        if kind in ("R", "C"):
            old_path, path = tokens[i], tokens[i + 1]
            i += 2
        else:
            old_path, path = None, tokens[i]
            i += 1
        changes.append(Change(kind, old_blob, new_blob, path, old_path))
    return Entry(commit, tuple(changes))

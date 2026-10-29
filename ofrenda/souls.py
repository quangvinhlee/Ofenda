"""Turn history into souls: deleted files, reverted commits, quiet contributors."""

import re
from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Literal, Sequence

from .history import Commit, Entry

_REVERT = re.compile(r'^Revert "(.+)"$')

EMPTY_BLOB = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"

DEFAULT_IGNORES: tuple[str, ...] = (
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "*.lock", "*.min.js", "*.map",
    "*.snap", "node_modules/", "vendor/", "dist/", "build/",
)


def is_ignored(path: str, patterns: Sequence[str]) -> bool:
    parts = path.split("/")
    base = parts[-1]
    for pat in patterns:
        if pat.endswith("/"):
            if pat.rstrip("/") in parts[:-1]:
                return True
        elif fnmatch(path, pat) or fnmatch(base, pat):
            return True
    return False


@dataclass(frozen=True)
class Return:
    commit: Commit
    path: str
    exact: bool


@dataclass
class Soul:
    id: str
    kind: Literal["file", "revert", "contributor"]
    name: str
    born: Commit
    died: Commit
    last_words: str
    touches: int
    authors: list[str]
    former_names: list[str] = field(default_factory=list)
    blob: str | None = None
    returned: Return | None = None
    lines_at_death: int | None = None

    @property
    def lifespan_days(self) -> int:
        return max(0, (self.died.date - self.born.date).days)


@dataclass
class _Track:
    born: Commit
    touches: int = 0
    authors: list[str] = field(default_factory=list)
    former_names: list[str] = field(default_factory=list)

    def touch(self, commit: Commit) -> None:
        self.touches += 1
        if commit.author not in self.authors:
            self.authors.append(commit.author)


def find_file_souls(history: list[Entry], ignores: Sequence[str] = DEFAULT_IGNORES) -> list[Soul]:
    live: dict[str, _Track] = {}
    by_blob: dict[str, Soul] = {}
    by_path: dict[str, Soul] = {}
    souls: list[Soul] = []

    def bury(soul: Soul) -> None:
        if soul.blob and soul.blob != EMPTY_BLOB:
            by_blob[soul.blob] = soul
        by_path[soul.name] = soul

    def resurrect(soul: Soul, commit: Commit, path: str, exact: bool) -> None:
        soul.returned = Return(commit, path, exact)
        if soul.blob and by_blob.get(soul.blob) is soul:
            del by_blob[soul.blob]
        if by_path.get(soul.name) is soul:
            del by_path[soul.name]

    for entry in history:
        commit = entry.commit
        for ch in entry.changes:
            if ch.status in ("A", "C"):
                ghost = by_blob.get(ch.new_blob) if ch.new_blob != EMPTY_BLOB else None
                if ghost is not None:
                    resurrect(ghost, commit, ch.path, exact=True)
                elif (ghost := by_path.get(ch.path)) is not None:
                    resurrect(ghost, commit, ch.path, exact=False)
                track = live[ch.path] = _Track(commit)
                track.touch(commit)
            elif ch.status == "R":
                track = live.pop(ch.old_path, None) or _Track(commit)
                track.former_names.append(ch.old_path)
                track.touch(commit)
                live[ch.path] = track
            elif ch.status == "D":
                track = live.pop(ch.path, None) or _Track(commit)
                track.touch(commit)
                if is_ignored(ch.path, ignores):
                    continue
                soul = Soul(
                    id=f"file:{ch.path}:{commit.sha[:12]}", kind="file", name=ch.path,
                    born=track.born, died=commit, last_words=commit.subject,
                    touches=track.touches, authors=track.authors,
                    former_names=track.former_names, blob=ch.old_blob,
                )
                souls.append(soul)
                bury(soul)
            else:  # M, T, and anything unexpected
                live.setdefault(ch.path, _Track(commit)).touch(commit)
    return souls


def find_revert_souls(history: list[Entry]) -> list[Soul]:
    souls: list[Soul] = []
    latest_by_subject: dict[str, Commit] = {}
    for entry in history:
        commit = entry.commit
        m = _REVERT.match(commit.subject)
        if m and (original := latest_by_subject.get(m.group(1))) is not None:
            authors = list(dict.fromkeys([original.author, commit.author]))
            souls.append(Soul(
                id=f"revert:{commit.sha[:12]}", kind="revert", name=m.group(1),
                born=original, died=commit, last_words=commit.subject,
                touches=1, authors=authors,
            ))
        latest_by_subject[commit.subject] = commit
    return souls


def find_quiet_contributors(history: list[Entry], quiet_days: int = 365,
                            min_commits: int = 5) -> list[Soul]:
    if not history:
        return []
    now = history[-1].commit.date
    first: dict[str, Commit] = {}
    last: dict[str, Commit] = {}
    count: dict[str, int] = {}
    for entry in history:
        c = entry.commit
        key = c.email.lower()
        first.setdefault(key, c)
        if key not in last or c.date >= last[key].date:
            last[key] = c
        count[key] = count.get(key, 0) + 1
    souls: list[Soul] = []
    for key, n in count.items():
        final = last[key]
        if n < min_commits or (now - final.date).days < quiet_days:
            continue
        souls.append(Soul(
            id=f"contributor:{key}", kind="contributor", name=final.author,
            born=first[key], died=final, last_words=final.subject,
            touches=n, authors=[final.author],
        ))
    return souls

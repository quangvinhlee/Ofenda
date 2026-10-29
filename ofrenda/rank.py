"""Choose which souls make it onto the altar."""

from pathlib import Path

from .git import GitError, run_git
from .souls import Soul

REVERT_QUOTA = 3
CONTRIBUTOR_QUOTA = 3


def score(soul: Soul) -> float:
    return (min(soul.lifespan_days, 3650) / 30 + 2 * soul.touches + 3 * len(soul.authors)
            + (25 if soul.returned else 0))


def _newest(soul: Soul) -> float:
    return -soul.died.date.timestamp()


def select(souls: list[Soul], top: int = 8) -> list[Soul]:
    files = sorted((s for s in souls if s.kind == "file"), key=lambda s: (-score(s), _newest(s)))
    reverts = sorted((s for s in souls if s.kind == "revert"),
                     key=lambda s: (-s.lifespan_days, _newest(s)))
    people = sorted((s for s in souls if s.kind == "contributor"),
                    key=lambda s: (-s.touches, _newest(s)))
    return files[:top] + reverts[:REVERT_QUOTA] + people[:CONTRIBUTOR_QUOTA]


def ghosts(souls: list[Soul], limit: int = 5) -> list[Soul]:
    back = [s for s in souls if s.returned is not None]
    back.sort(key=lambda s: (not s.returned.exact, -score(s), _newest(s)))
    return back[:limit]


def enrich_lines(repo: Path, souls: list[Soul]) -> None:
    """Count each deleted file's lines from its blob at death; binary or missing stays None."""
    for soul in souls:
        if soul.kind != "file" or not soul.blob:
            continue
        try:
            text = run_git(repo, "cat-file", "-p", soul.blob)
        except GitError:
            continue
        if "\x00" in text[:8000]:
            continue
        soul.lines_at_death = len(text.splitlines())

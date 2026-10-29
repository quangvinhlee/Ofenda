"""Everything a renderer needs, in one object."""

from dataclasses import dataclass
from datetime import datetime

from .souls import Soul


@dataclass
class Altar:
    repo_name: str
    commit_count: int
    first_date: datetime
    last_date: datetime
    souls: list[Soul]
    ghosts: list[Soul]
    verses: dict[str, tuple[str, str]]  # soul id -> (verse, "model" | "template")
    model: str | None

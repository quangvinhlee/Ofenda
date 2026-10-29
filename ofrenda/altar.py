"""Everything a renderer needs, in one object."""

import re
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


_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
MAX_TEXT = 200


def clean_text(value: object, limit: int = MAX_TEXT) -> str:
    """Display-safe text: no control characters (so no escape sequences), bounded length."""
    text = _CONTROL.sub(" ", str(value)).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def source_label(altar: Altar, soul: Soul) -> str:
    _, source = altar.verses.get(soul.id, ("", "template"))
    if source == "model" and altar.model:
        return f"calavera · written locally by {altar.model}"
    return "calavera · template (model offline)"


def footer(altar: Altar) -> str:
    if altar.model and any(src == "model" for _, src in altar.verses.values()):
        return f"facts from git · verses by {altar.model} on this machine"
    return "facts from git · verses from a template"


def subtitle(altar: Altar) -> str:
    return f"{altar.commit_count} commits · {altar.first_date:%Y} – {altar.last_date:%Y}"


def ghost_line(soul: Soul) -> str:
    r = soul.returned
    how = "exact same content" if r.exact else "same name, new body"
    return (f"{clean_text(soul.name)} → {clean_text(r.path)} ({how}) · "
            f"{r.commit.date:%Y-%m-%d}, after {soul.days_gone} days")


def fact_rows(soul: Soul) -> list[tuple[str, str]]:
    """The facts on a card, already display-cleaned (HTML still needs escaping)."""
    rows = [
        ("born", f"{soul.born.date:%Y-%m-%d} · {clean_text(soul.born.author, 60)}"),
        ("died", f"{soul.died.date:%Y-%m-%d} · {clean_text(soul.died.author, 60)}"),
        ("lifespan", f"{soul.lifespan_days} days"),
        ("commits" if soul.kind == "contributor" else "touches", str(soul.touches)),
    ]
    if soul.lines_at_death is not None:
        rows.append(("lines at death", str(soul.lines_at_death)))
    if soul.former_names:
        rows.append(("once known as", clean_text(", ".join(soul.former_names))))
    rows.append(("last words", f"\"{clean_text(soul.last_words)}\""))
    return rows

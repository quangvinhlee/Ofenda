"""The altar in a terminal. Every dynamic string goes in as `Text`, never as markup."""

from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .altar import Altar, clean_text, fact_rows, footer, ghost_line, source_label, subtitle
from .souls import Soul

MARIGOLD = "#F2A007"
MAGENTA = "#D6336C"
VIOLET = "#7048E8"
TITLE_WIDTH = 38

_KIND_ICON = {"file": "📄", "revert": "↩️ ", "contributor": "🕊️ "}


def render_terminal(altar: Altar, console: Console) -> None:
    banner = Text(justify="center")
    banner.append(f"🕯️  OFRENDA · {clean_text(altar.repo_name, 60)}  🕯️\n", style=f"bold {MARIGOLD}")
    banner.append("🌼 " * 16 + "\n")
    banner.append(subtitle(altar), style="dim")
    console.print(Align.center(banner))
    console.print()

    if altar.ghosts:
        lines = Text("\n").join(Text(ghost_line(g)) for g in altar.ghosts)
        console.print(Panel(lines, title=Text("👻 They came back", style=f"bold {VIOLET}"),
                            border_style=VIOLET, title_align="left"))
        console.print()

    if not altar.souls:
        console.print(Align.center(Text("Nobody has died here. Yet.", style=f"italic {MARIGOLD}")))
    else:
        cards = [_card(altar, s) for s in altar.souls]
        console.print(Columns(cards, equal=True, expand=True))

    console.print()
    console.print(Align.center(Text(footer(altar), style="dim")))


def _card(altar: Altar, soul: Soul) -> Panel:
    facts = Table.grid(padding=(0, 1))
    facts.add_column(style="dim", no_wrap=True)
    facts.add_column(overflow="fold")
    for label, value in fact_rows(soul):
        facts.add_row(Text(label), Text(value))

    verse, _ = altar.verses.get(soul.id, ("", "template"))
    body = Group(
        facts,
        Rule(style=MAGENTA),
        Text("\n".join(clean_text(line, 120) for line in verse.splitlines()), style="italic"),
        Text(source_label(altar, soul), style="dim"),
    )
    name = clean_text(soul.name)
    if len(name) > TITLE_WIDTH:  # keep the filename, drop the front of the path
        name = "…" + name[-(TITLE_WIDTH - 1):]
    title = Text(f"{_KIND_ICON.get(soul.kind, '')} ") + Text(name, style="bold")
    border = VIOLET if soul.returned else MARIGOLD
    return Panel(body, title=title, title_align="left", border_style=border, width=48)

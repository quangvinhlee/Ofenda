"""The altar in a terminal. Every dynamic string goes in as `Text`, never as markup."""

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .altar import Altar, clean_text, fact_rows, footer, ghost_line, source_label, subtitle
from .rank import is_ghost
from .souls import Soul

MARIGOLD = "#F2A007"
PUMPKIN = "#F76707"
MAGENTA = "#D6336C"
VIOLET = "#7048E8"
BONE = "#F1E3D3"
TITLE_WIDTH = 38

_KIND_ICON = {"file": "💀", "revert": "⚰️ ", "contributor": "🕊️ "}

# A 5-row block font, just enough letters for the banner.
_FONT = {
    "O": [" ███ ", "█   █", "█   █", "█   █", " ███ "],
    "F": ["████", "█   ", "███ ", "█   ", "█   "],
    "R": ["████ ", "█   █", "████ ", "█  █ ", "█   █"],
    "E": ["████", "█   ", "███ ", "█   ", "████"],
    "N": ["█   █", "██  █", "█ █ █", "█  ██", "█   █"],
    "D": ["████ ", "█   █", "█   █", "█   █", "████ "],
    "A": [" ███ ", "█   █", "█████", "█   █", "█   █"],
}
_GRADIENT = ((0xF7, 0x67, 0x07), (0xD6, 0x33, 0x6C), (0x70, 0x48, 0xE8))  # pumpkin → magenta → violet


def _gradient(t: float) -> str:
    """Color at position t in [0, 1] along the pumpkin-to-violet gradient."""
    seg = min(int(t * (len(_GRADIENT) - 1)), len(_GRADIENT) - 2)
    local = t * (len(_GRADIENT) - 1) - seg
    a, b = _GRADIENT[seg], _GRADIENT[seg + 1]
    r, g, bl = (round(x + (y - x) * local) for x, y in zip(a, b))
    return f"#{r:02x}{g:02x}{bl:02x}"


def _big_word(word: str) -> Text:
    rows = ["  ".join(_FONT[ch][i] for ch in word) for i in range(5)]
    width = len(rows[0])
    out = Text()
    for i, row in enumerate(rows):
        for col, ch in enumerate(row):
            out.append(ch, style=f"bold {_gradient(col / max(width - 1, 1))}")
        if i < len(rows) - 1:
            out.append("\n")
    return out


def _banner(altar: Altar, console: Console) -> Group:
    sky = Text("🦇       ·    🌕    ·       🦇", style=BONE)
    if console.width >= 52:
        title = _big_word("OFRENDA")
    else:
        title = Text("OFRENDA", style=f"bold {PUMPKIN}")
    repo = Text(f"🕯️  {clean_text(altar.repo_name, 60)}  🕯️", style=f"bold {MARIGOLD}")
    border = Text("🎃 🌼 💀 🌼 🕯️  🌼 🎃 🌼 🕯️  🌼 💀 🌼 🎃", style=MARIGOLD)
    return Group(*(Align.center(t) for t in (sky, title, Text(""), repo, border,
                                             Text(subtitle(altar), style="dim"))))


def _census(altar: Altar) -> Panel:
    grid = Table.grid(padding=(0, 1))
    grid.add_column(style="dim", no_wrap=True)
    grid.add_column(no_wrap=True)
    grid.add_column(justify="right", style="bold")
    biggest = max(altar.census.values(), default=0) or 1
    colors = (PUMPKIN, MAGENTA, VIOLET, MARIGOLD)
    for i, (label, n) in enumerate(altar.census.items()):
        bar = "█" * max(1, round(28 * n / biggest)) if n else "·"
        grid.add_row(Text(label), Text(bar, style=colors[i % len(colors)]), Text(str(n)))
    return Panel(grid, title=Text("⚰️  Graveyard census", style=f"bold {PUMPKIN}"),
                 title_align="left", border_style=PUMPKIN, box=box.HEAVY, expand=False)


def render_terminal(altar: Altar, console: Console) -> None:
    console.print(_banner(altar, console))
    console.print()

    if altar.census:
        console.print(Align.center(_census(altar)))
        console.print()

    if altar.ghosts:
        lines = Text("\n").join(Text(ghost_line(g)) for g in altar.ghosts)
        console.print(Panel(lines, title=Text("👻 They came back", style=f"bold {VIOLET}"),
                            border_style=VIOLET, box=box.DOUBLE, title_align="left"))
        console.print()

    if not altar.souls:
        console.print(Align.center(Text("Nobody has died here. Yet.", style=f"italic {MARIGOLD}")))
    else:
        cards = [_card(altar, s) for s in altar.souls]
        console.print(Columns(cards, equal=True, expand=True))

    console.print()
    console.print(Align.center(Text(f"🦇 {footer(altar)} 🦇", style="dim")))


def _card(altar: Altar, soul: Soul) -> Panel:
    facts = Table.grid(padding=(0, 1))
    facts.add_column(style="dim", no_wrap=True)
    facts.add_column(overflow="fold")
    for label, value in fact_rows(soul):
        facts.add_row(Text(label), Text(value))

    ghost = is_ghost(soul)
    verse, _ = altar.verses.get(soul.id, ("", "template"))
    body = Group(
        Align.center(Text("R.I.P.", style=f"bold {BONE}")),
        facts,
        Rule(style=MAGENTA),
        Text("\n".join(clean_text(line, 120) for line in verse.splitlines()), style="italic"),
        Text(source_label(altar, soul), style="dim"),
    )
    name = clean_text(soul.name)
    if len(name) > TITLE_WIDTH:  # keep the filename, drop the front of the path
        name = "…" + name[-(TITLE_WIDTH - 1):]
    icon = "👻" if ghost else _KIND_ICON.get(soul.kind, "")
    title = Text(f"{icon} ") + Text(name, style="bold")
    dates = Text(f"✝ {soul.born.date:%Y} – {soul.died.date:%Y}", style="dim")
    border = VIOLET if ghost else PUMPKIN
    return Panel(body, title=title, title_align="left", subtitle=dates, subtitle_align="right",
                 border_style=border, box=box.ROUNDED, width=48)

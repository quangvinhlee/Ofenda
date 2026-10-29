from datetime import UTC, datetime

from rich.console import Console

from ofrenda.altar import Altar
from ofrenda.history import Commit
from ofrenda.render_terminal import render_terminal
from ofrenda.souls import Return, Soul

MODEL = "gemma4:e2b"


def make_soul(name="old.py", last_words="remove legacy", returned=None, **overrides) -> Soul:
    born = Commit("a" * 40, "Ana", "a@x", datetime(2020, 1, 1, tzinfo=UTC), "born")
    died = Commit("b" * 40, "Bo", "b@x", datetime(2021, 1, 1, tzinfo=UTC), last_words)
    fields = dict(id=f"file:{name}:bbbbbbbbbbbb", kind="file", name=name, born=born, died=died,
                  last_words=last_words, touches=3, authors=["Ana", "Bo"], returned=returned,
                  lines_at_death=12, former_names=["older.py"])
    fields.update(overrides)
    return Soul(**fields)


def make_altar(souls=None, ghosts=None, source="model", model=MODEL) -> Altar:
    souls = [make_soul()] if souls is None else souls
    ghosts = [] if ghosts is None else ghosts
    verses = {s.id: ("Line one\nLine two\nLine three\nLine four", source) for s in souls + ghosts}
    return Altar("demo", 42, datetime(2019, 5, 1, tzinfo=UTC), datetime(2026, 10, 1, tzinfo=UTC),
                 souls, ghosts, verses, model)


def terminal_text(altar: Altar) -> str:
    console = Console(record=True, width=100, color_system=None)
    render_terminal(altar, console)
    return console.export_text()


def test_terminal_shows_facts_and_label():
    back = Return(Commit("c" * 40, "Cy", "c@x", datetime(2022, 2, 2, tzinfo=UTC), "back"),
                  "new/old.py", exact=True)
    ghost = make_soul(returned=back)
    out = terminal_text(make_altar(souls=[ghost], ghosts=[ghost]))
    assert "old.py" in out and "remove legacy" in out
    assert "calavera · written locally by gemma4:e2b" in out
    assert "👻 They came back" in out
    assert "new/old.py" in out and "exact same content" in out
    assert "42 commits · 2019 – 2026" in out
    assert "verses by gemma4:e2b on this machine" in out


def test_terminal_template_label():
    out = terminal_text(make_altar(source="template", model=None))
    assert "calavera · template (model offline)" in out
    assert "verses from a template" in out


def test_terminal_escapes_markup():
    out = terminal_text(make_altar(souls=[make_soul(name="[bold red]x[/] .py")]))
    assert "[bold red]x[/] .py" in out


def test_terminal_strips_control_sequences():
    console = Console(record=True, width=100, force_terminal=True)
    render_terminal(make_altar(souls=[make_soul(last_words="evil \x1b]0;pwned\x07\x1b[2J")]), console)
    out = console.export_text(styles=False)
    assert "\x1b" not in out and "\x07" not in out and "evil" in out


def test_terminal_long_name_keeps_filename():
    out = terminal_text(make_altar(souls=[make_soul(name="a/very/long/path/to/some/deeply/nested/module_name.py")]))
    assert "module_name.py" in out


def test_terminal_empty_altar():
    assert "Nobody has died here. Yet." in terminal_text(make_altar(souls=[]))

"""`git ofrenda`: build an altar for what died in a repository's history."""

import argparse
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.text import Text

from .altar import Altar, clean_text
from .calavera import CalaveraWriter, fallback_verse
from .git import GitError, git_dir, is_shallow, run_git
from .history import read_history
from .rank import enrich_lines, ghosts, is_ghost, select
from .render_html import render_html
from .render_terminal import render_terminal
from .souls import DEFAULT_IGNORES, find_file_souls, find_quiet_contributors, find_revert_souls

DEFAULT_MODEL = "gemma4:e2b"
DEFAULT_HOST = "http://127.0.0.1:11434"


def _positive(value: str) -> int:
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return n


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="git ofrenda",
        description="Build a Día de los Muertos altar for the files, reverts and contributors "
                    "that died in a git repository. Facts come from git; a local model writes the verses.",
    )
    p.add_argument("path", nargs="?", default=".", help="repository to scan (default: .)")
    p.add_argument("--top", type=_positive, default=8, metavar="N", help="deleted files to show (default: 8)")
    p.add_argument("--model", default=os.environ.get("OFRENDA_MODEL", DEFAULT_MODEL), metavar="M",
                   help=f"Ollama model for the verses (default: $OFRENDA_MODEL or {DEFAULT_MODEL})")
    p.add_argument("--host", default=DEFAULT_HOST, metavar="URL", help=f"Ollama host (default: {DEFAULT_HOST})")
    p.add_argument("--lang", choices=("en", "es"), default="en", help="verse language (default: en)")
    p.add_argument("--no-ai", action="store_true", help="template verses only, no network")
    p.add_argument("--include-people", action="store_true", help="also mourn contributors who went quiet")
    p.add_argument("--quiet-days", type=_positive, default=365, metavar="N",
                   help="days without a commit before a contributor counts as quiet (default: 365)")
    p.add_argument("--ignore", action="append", default=[], metavar="PATTERN",
                   help="extra path pattern to skip (repeatable; adds to the defaults)")
    p.add_argument("--html", type=Path, metavar="PATH", help="also write the altar as one HTML page")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    console = Console(highlight=False)
    repo = Path(args.path)

    try:
        history = read_history(repo)
    except GitError:
        print(f"ofrenda: {args.path} is not a git repository", file=sys.stderr)
        return 2
    if not history:
        console.print("No history yet — nothing has died.")
        return 0
    if is_shallow(repo):
        console.print("shallow clone: older history is missing; run git fetch --unshallow "
                      "for the full altar", style="yellow")

    souls = find_file_souls(history, (*DEFAULT_IGNORES, *args.ignore)) + find_revert_souls(history)
    if args.include_people:
        souls += find_quiet_contributors(history, quiet_days=args.quiet_days)
    chosen = select(souls, top=args.top)
    back = ghosts(souls)
    enrich_lines(repo, list({s.id: s for s in chosen + back}.values()))

    verses: dict[str, tuple[str, str]] = {}
    writer = None
    if not args.no_ai:
        writer = CalaveraWriter(args.model, host=args.host, lang=args.lang,
                                cache_path=git_dir(repo) / "ofrenda" / "calaveras.json")
    warned = False
    with console.status("lighting candles…", spinner="moon") as status:
        todo = list({s.id: s for s in chosen + back}.values())
        for soul in todo:
            if soul.id in verses:
                continue
            if writer is None:
                verses[soul.id] = (fallback_verse(soul), "template")
                continue
            status.update(Text(f"🎃 lighting candles for {clean_text(soul.name, 60)}… "
                               f"({len(verses) + 1}/{len(todo)})"))
            verses[soul.id] = writer.write(soul)
            if writer.offline_reason and not warned:
                console.print(Text(f"model offline ({clean_text(writer.offline_reason)}); "
                                   "using template verses", style="dim"))
                warned = True

    altar = Altar(
        repo_name=_repo_name(repo),
        commit_count=len(history),
        first_date=min(e.commit.date for e in history),
        last_date=max(e.commit.date for e in history),
        souls=chosen,
        ghosts=back,
        verses=verses,
        model=None if writer is None else args.model,
        census=_census(souls, args.include_people),
    )
    render_terminal(altar, console)

    if args.html:
        try:
            args.html.write_text(render_html(altar), encoding="utf-8")
        except OSError as e:
            print(f"ofrenda: could not write {args.html}: {e.strerror or e}", file=sys.stderr)
            return 1
        console.print(Text(f"altar written to {args.html}"))
    return 0


def _census(souls: list, include_people: bool) -> dict[str, int]:
    census = {
        "deleted files": sum(s.kind == "file" for s in souls),
        "reverts": sum(s.kind == "revert" for s in souls),
        "ghosts": sum(is_ghost(s) for s in souls),
    }
    if include_people:
        census["went quiet"] = sum(s.kind == "contributor" for s in souls)
    return census


def _repo_name(repo: Path) -> str:
    try:
        return Path(run_git(repo, "rev-parse", "--show-toplevel").strip()).name
    except GitError:  # bare repository
        return git_dir(repo).name.removesuffix(".git") or "repo"


def run() -> None:
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)

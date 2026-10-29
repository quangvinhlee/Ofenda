"""The one place that runs git."""

import subprocess
from pathlib import Path


class GitError(Exception):
    """git exited nonzero (or could not be run at all)."""


def run_git(repo: Path, *args: str) -> str:
    cmd = ["git", "-c", "core.quotePath=false", "-c", "log.showSignature=false", *args]
    try:
        proc = subprocess.run(cmd, cwd=repo, capture_output=True)
    except (FileNotFoundError, NotADirectoryError) as e:
        raise GitError(str(e)) from e
    if proc.returncode != 0:
        raise GitError(proc.stderr.decode("utf-8", errors="replace").strip())
    return proc.stdout.decode("utf-8", errors="replace")


def git_dir(repo: Path) -> Path:
    return Path(run_git(repo, "rev-parse", "--absolute-git-dir").strip())


def is_shallow(repo: Path) -> bool:
    return run_git(repo, "rev-parse", "--is-shallow-repository").strip() == "true"

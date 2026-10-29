# Git Ofrenda Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `git ofrenda` scans a repository's entire git history, finds what has "died" (deleted files, reverted commits, optionally contributors who went quiet), detects what came back from the dead, and builds a Día de los Muertos altar in the terminal and as a single HTML page. A local open-weight model writes a *calavera literaria* (a short satirical memorial verse) for each soul.

**Architecture:** One streaming pass over `git log --raw -z` produces typed history entries. Pure functions turn those into `Soul` records, rank them and enrich the winners. A swappable Ollama client writes the verses, with a deterministic fallback. Two renderers (rich terminal, static HTML) consume the same `Altar` object. **Facts always come from git. Only the verse comes from the model, and the UI labels it as such.**

**Tech Stack:** Python ≥ 3.11 (dev machine: 3.14), `git` CLI via `subprocess`, `rich` (terminal UI), the Ollama HTTP API through `urllib` (no SDK), `pytest`.

**Spec:** This document. The design was settled in chat on 2026-10-30, and the "Design" section below is the spec.

**Deadline:** DEV Hacktoberfest Week 4 ("Ghost in the Machine") submissions close **2026-10-31 23:59 PDT (2026-11-01 06:59 UTC)**. Target categories: **Overall** and **Gemma** (featured: "use Gemma, Google's open-weight model… run it locally"). Each person can win at most one prize. Required tags: `#devchallenge #hf26challenge`. The post needs a demo (video or link) and the repo link. Writing quality carries the most weight in judging. Work must start on or after 2026-10-26, so the first commit is the evidence. Suggested schedule: Tasks 1–5 on Oct 30, Tasks 6–8 the morning of Oct 31, Task 9 (demo and post) in the afternoon of Oct 31. If time runs short, cut in this order: Task 7 (HTML), then `--include-people`, then the calavera cache.

---

## Design

### What counts as a soul

| kind | detected from | born | died | last words |
|---|---|---|---|---|
| `file` | a `D` entry in the raw log; the file's history is followed through `R` renames | first `A` (or first sighting) of the lineage | the deleting commit | the deleting commit's subject |
| `revert` | a commit whose subject matches `^Revert "(.+)"$` | latest earlier commit whose subject equals the captured text | the revert commit | the revert commit's subject |
| `contributor` (opt-in) | an author (by mailmapped email) with ≥ 5 commits whose last commit is ≥ `quiet_days` (default 365) older than HEAD's commit date | their first commit | their last commit | their last commit's subject |

### Ghosts: the dead who return

When a `file` soul has died and a later `A` (or `C`) entry appears:

- **exact return**: the new blob SHA equals the soul's blob at death. Git hashes content, so this is proof, not a guess.
- **same-name return**: same path, different content. Only recorded when there was no exact return.

The empty blob `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` never counts as an exact return, because every empty `__init__.py` / `.gitkeep` would otherwise "resurrect" every other one. Only the *first* return of a soul is recorded.

### Noise filter

These default ignore patterns apply to `file` souls only: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `*.lock`, `*.min.js`, `*.map`, `*.snap`, `node_modules/`, `vendor/`, `dist/`, `build/`. A pattern ending in `/` matches that directory as a component anywhere in the path. Any other pattern is `fnmatch`ed against both the full path and the basename. `--ignore` adds to the defaults.

### Ranking

Score for a `file` soul: `min(lifespan_days, 3650) / 30 + 2 * touches + 3 * len(authors) + (25 if returned else 0)`.

The altar shows:
- up to `--top` (default 8) file souls
- up to 3 revert souls (longest lifespan first)
- up to 3 contributor souls (most commits first)

A separate **Ghosts** section lists up to 5 returned souls, exact returns first, which may overlap with the main list. Ties break by death date, newest first.

### Why open-source AI matters here (for the post)

Private history, including deleted code and possibly deleted secrets, never leaves the laptop. It works offline. Swapping the model is one flag (`--model`). It's free on repos with thousands of commits. The verse is decoration on top of facts that git provides.

## Global Constraints

- Python `>=3.11`. Runtime dependencies: `rich` only. Dev dependency: `pytest`.
- Network: only the Ollama host (default `http://127.0.0.1:11434`). The HTML output loads **nothing** external (no fonts, no CDNs), so it works offline.
- The tool never writes to the scanned repo's working tree. The only writes are `<git-dir>/ofrenda/calaveras.json` (cache) and the `--html` path.
- Default model: `gemma4:e2b` (already pulled on the dev machine; it gave better verses than `gemma3:4b-it-q4_K_M`, which is also pulled and serves as the swap demo). gemma4 is a thinking model: without `"think": false` it spends the whole `num_predict` budget thinking and returns an empty response (verified 2026-10-30). The `OFRENDA_MODEL` env var or `--model` overrides it.
- Every git call goes through `run_git` with `-c core.quotePath=false`, and output is decoded as UTF-8 with `errors="replace"`.
- The model never supplies facts. The verse is always shown under a label naming its source: `calavera · written locally by <model>`, or `calavera · template (model offline)`.

## Review Focus

1. **Odd paths** (spaces, unicode, a path that is renamed and then deleted). Expect correct names and a single lineage. Tested in Task 1 (`test_parses_spaces_and_unicode`) and Task 2 (`test_rename_then_delete_is_one_soul`).
2. **Empty and common blobs.** Deleting `a/__init__.py` and later adding an empty `b/__init__.py` must *not* create a ghost. Tested in Task 2 (`test_empty_blob_never_resurrects`).
3. **Ollama down, model not pulled, or slow output.** The run still completes with template verses, the user is warned once, and the tool does not wait out a timeout per soul. Tested in Task 5 (`test_unreachable_host_falls_back_once`).
4. **Hostile text in commit messages or file names** (`<script>`, very long subjects, ANSI escapes). The HTML is escaped and terminal output can't be hijacked. Tested in Task 7 (`test_html_escapes_everything`) and Task 6 (`test_terminal_escapes_markup`).
5. **Not a repo, an empty repo, a shallow clone, or a history with a delete before any add.** Expect a clear message and the right exit code, never a traceback. Tested in Task 1 (`test_not_a_repo_raises`), Task 2 (`test_delete_without_birth_synthesizes`) and Task 8 (`test_cli_*`).

---

## File Structure

```
Ofrenda/
  PLAN.md
  README.md                 # Task 9
  pyproject.toml            # Task 1
  ofrenda/
    __init__.py
    git.py                  # run_git, GitError, git_dir, is_shallow           (Task 1)
    history.py              # Commit, Change, Entry, read_history             (Task 1)
    souls.py                # Soul, Return, find_file_souls, find_revert_souls,
                            # find_quiet_contributors, is_ignored               (Tasks 2–3)
    rank.py                 # score, select, ghosts, enrich_lines             (Task 4)
    calavera.py             # CalaveraWriter, fallback_verse, clean_verse     (Task 5)
    altar.py                # Altar dataclass                                 (Task 4)
    render_terminal.py      # render_terminal                                 (Task 6)
    render_html.py          # render_html                                     (Task 7)
    cli.py                  # main, run                                       (Task 8)
  tests/
    conftest.py             # `repo` fixture → RepoBuilder                     (Task 1)
    test_history.py  test_souls.py  test_rank.py  test_calavera.py
    test_render.py   test_cli.py
```

---

### Task 1: Project scaffold, git runner, history parser

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `ofrenda/__init__.py`, `ofrenda/git.py`, `ofrenda/history.py`, `tests/conftest.py`, `tests/test_history.py`

**Interfaces:**
- Produces:
  - `class GitError(Exception)`
  - `run_git(repo: Path, *args: str) -> str` raises `GitError(stderr)` on a nonzero exit
  - `git_dir(repo: Path) -> Path` (absolute, via `rev-parse --absolute-git-dir`)
  - `is_shallow(repo: Path) -> bool`
  - `@dataclass(frozen=True) Commit(sha: str, author: str, email: str, date: datetime, subject: str)`
  - `@dataclass(frozen=True) Change(status: str, old_blob: str, new_blob: str, path: str, old_path: str | None)`, where `status` is the first letter only (`"R100"` becomes `"R"`)
  - `@dataclass(frozen=True) Entry(commit: Commit, changes: tuple[Change, ...])`
  - `read_history(repo: Path) -> list[Entry]`, oldest first; returns `[]` for a repo with no commits
  - Test fixture `repo` gives a `RepoBuilder` with `write(path, text)`, `delete(path)`, `rename(old, new)`, `commit(msg, author="Ana <ana@example.com>", date="2020-01-01T12:00:00+00:00") -> str` (returns the sha), and `.path`

- [ ] **Step 1: Scaffold.** `git init -b main` in `Ofrenda/`. In `pyproject.toml`, set name `git-ofrenda`, `requires-python = ">=3.11"`, `dependencies = ["rich>=13"]`, the optional `dev = ["pytest>=8"]`, and `[project.scripts] git-ofrenda = "ofrenda.cli:run"`. In `.gitignore`, list `.venv/`, `__pycache__/`, `*.egg-info/`, `ofrenda.html`. Create the venv: `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`. (`cli.py` doesn't exist yet. That's fine until Task 8.)

- [ ] **Step 2: Write `tests/conftest.py`.** `RepoBuilder` runs `git init -b main` in `tmp_path / "r"`, sets `user.name`/`user.email`, and commits with `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` and `--author` so the tests are deterministic.

- [ ] **Step 3: Write the failing tests** in `tests/test_history.py`

```python
def test_reads_add_modify_delete_oldest_first(repo):
    repo.write("a.py", "x\n"); s1 = repo.commit("born", date="2020-01-01T00:00:00+00:00")
    repo.write("a.py", "y\n"); repo.commit("grow")
    repo.delete("a.py");       s3 = repo.commit("goodbye")
    h = read_history(repo.path)
    assert [e.commit.subject for e in h] == ["born", "grow", "goodbye"]
    assert h[0].commit.sha == s1 and h[0].commit.date.year == 2020
    assert [(c.status, c.path) for c in h[2].changes] == [("D", "a.py")]
    assert h[2].changes[0].old_blob == h[1].changes[0].new_blob

def test_parses_spaces_and_unicode(repo):
    repo.write("a b.txt", "1\n"); repo.write("ñ.py", "2\n"); repo.commit("born")
    repo.rename("ñ.py", "moved ñ.py"); repo.commit("move")
    h = read_history(repo.path)
    assert sorted(c.path for c in h[0].changes) == ["a b.txt", "ñ.py"]
    (r,) = h[1].changes
    assert (r.status, r.old_path, r.path) == ("R", "ñ.py", "moved ñ.py")

def test_empty_repo_has_no_history(repo):
    assert read_history(repo.path) == []

def test_not_a_repo_raises(tmp_path):
    with pytest.raises(GitError):
        read_history(tmp_path)
```

- [ ] **Step 4: Run** `.venv/bin/pytest tests/test_history.py -v`. Expected: FAIL (ImportError).

- [ ] **Step 5: Implement `git.py` and `history.py`.** Run:

`git log -z --reverse --date-order --raw --no-abbrev -M --use-mailmap --format=%x1e%H%x1f%aN%x1f%aE%x1f%aI%x1f%s`

An empty repo makes `git log` fail with "does not have any commits". Check `rev-parse --verify -q HEAD` first and return `[]` if it fails.

The parser has been verified against real git output (2026-10-30). Split stdout on `\x1e` and drop the leading empty chunk. In each chunk, the header runs up to the first `\x00` and its fields are split on `\x1f`. The rest (after stripping a leading `\n`) is a NUL-separated token stream. A token starting with `:` is meta (`:oldmode newmode oldblob newblob STATUS`). For statuses `R` and `C`, the next two tokens are old_path and path. Otherwise one token is path.

- [ ] **Step 6: Run** `.venv/bin/pytest tests/test_history.py -v`. Expected: 4 passed.

- [ ] **Step 7: Commit** `feat: scaffold and git history parser`

---

### Task 2: File souls and ghosts

**Files:**
- Create: `ofrenda/souls.py`, `tests/test_souls.py`

**Interfaces:**
- Consumes: `Entry`, `Commit`, `Change` (Task 1)
- Produces:
  - `EMPTY_BLOB = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"`
  - `DEFAULT_IGNORES: tuple[str, ...]` (values from the Design section)
  - `is_ignored(path: str, patterns: Sequence[str]) -> bool`
  - `@dataclass(frozen=True) Return(commit: Commit, path: str, exact: bool)`
  - `@dataclass Soul(id: str, kind: Literal["file","revert","contributor"], name: str, born: Commit, died: Commit, last_words: str, touches: int, authors: list[str], former_names: list[str] = [], blob: str | None = None, returned: Return | None = None, lines_at_death: int | None = None)`, using `field(default_factory=list)` for the lists, plus the property `lifespan_days -> int` (`(died.date - born.date).days`, floored at 0)
  - `find_file_souls(history: list[Entry], ignores: Sequence[str] = DEFAULT_IGNORES) -> list[Soul]`. The id is `f"file:{path}:{died.sha[:12]}"`, `name` is the path at death, and `authors` are in order of first appearance.

- [ ] **Step 1: Write the failing tests**

```python
def test_deleted_file_becomes_soul(repo):
    repo.write("old.py", "a\n"); repo.commit("born", author="Ana <ana@x>", date="2020-01-01T00:00:00+00:00")
    repo.write("old.py", "b\n"); repo.commit("edit", author="Bo <bo@x>")
    repo.delete("old.py");       repo.commit("remove legacy", date="2021-01-01T00:00:00+00:00")
    (s,) = find_file_souls(read_history(repo.path))
    assert (s.kind, s.name, s.last_words) == ("file", "old.py", "remove legacy")
    assert s.lifespan_days == 366 and s.touches == 3 and s.authors == ["Ana", "Bo"]

def test_rename_then_delete_is_one_soul(repo):
    repo.write("a.py", "x\n"); repo.commit("born")
    repo.rename("a.py", "b.py"); repo.commit("move")
    repo.delete("b.py"); repo.commit("die")
    (s,) = find_file_souls(read_history(repo.path))
    assert s.name == "b.py" and s.former_names == ["a.py"] and s.born.subject == "born"

def test_exact_return_is_ghost(repo):
    repo.write("spell.py", "boo\n"); repo.commit("born")
    repo.delete("spell.py"); repo.commit("die")
    repo.write("elsewhere/spell2.py", "boo\n"); repo.commit("it's back")
    (s,) = find_file_souls(read_history(repo.path))
    assert s.returned.exact and s.returned.path == "elsewhere/spell2.py"

def test_same_name_return_is_not_exact(repo):
    repo.write("a.py", "1\n"); repo.commit("born")
    repo.delete("a.py"); repo.commit("die")
    repo.write("a.py", "2\n"); repo.commit("again")
    (s,) = find_file_souls(read_history(repo.path))
    assert s.returned is not None and not s.returned.exact

def test_empty_blob_never_resurrects(repo):
    repo.write("a/__init__.py", ""); repo.commit("born")
    repo.delete("a/__init__.py"); repo.commit("die")
    repo.write("b/__init__.py", ""); repo.commit("unrelated")
    (s,) = find_file_souls(read_history(repo.path))
    assert s.returned is None

def test_ignored_paths_skipped():
    assert is_ignored("web/node_modules/x/index.js", DEFAULT_IGNORES)
    assert is_ignored("deep/yarn.lock", DEFAULT_IGNORES)
    assert not is_ignored("src/builder.py", DEFAULT_IGNORES)

def test_delete_without_birth_synthesizes():
    # hand-built history: a D with no prior A (shallow clone / date-order quirk)
    c = Commit("f"*40, "Ana", "a@x", datetime(2020,1,1,tzinfo=UTC), "die")
    h = [Entry(c, (Change("D", "b"*40, "0"*40, "x.py", None),))]
    (s,) = find_file_souls(h)
    assert s.born == s.died and s.lifespan_days == 0
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_souls.py -v`. Expected: FAIL (ImportError).

- [ ] **Step 3: Implement.** Make one forward pass keeping `live: dict[path, _Track]`, where `_Track` holds born, touches, authors, former_names and blob, plus two graveyards, `by_blob` and `by_path`, which map to the most recent soul without a return. Handling by status:
  - **A / C:** check the graveyards first (exact by blob unless `EMPTY_BLOB`, else by path), then start a new track.
  - **M / T:** touch the track (create it if missing).
  - **R:** move the track to the new path, append to `former_names`, and touch it.
  - **D:** pop the track (synthesize it if missing), emit a `Soul`, and register it in the graveyards.

  Apply the ignore filter when emitting.

- [ ] **Step 4: Run** `.venv/bin/pytest tests/test_souls.py -v`. Expected: 7 passed.

- [ ] **Step 5: Commit** `feat: detect deleted files and ghosts`

---

### Task 3: Revert souls and quiet contributors

**Files:**
- Modify: `ofrenda/souls.py`, `tests/test_souls.py`

**Interfaces:**
- Produces:
  - `find_revert_souls(history: list[Entry]) -> list[Soul]`. The id is `f"revert:{died.sha[:12]}"`, `name` is the captured original subject, `touches=1`, and `authors=[original author, revert author]` (deduplicated). Skipped when the original commit isn't found.
  - `find_quiet_contributors(history: list[Entry], quiet_days: int = 365, min_commits: int = 5) -> list[Soul]`. Groups by email. The reference date is the last entry's commit date. The id is `f"contributor:{email}"`, `name` is the latest author name, and `touches` is the commit count.

- [ ] **Step 1: Write the failing tests**

```python
def test_revert_links_to_original(repo):
    repo.write("f.py", "1\n"); repo.commit("Add turbo mode", date="2020-01-01T00:00:00+00:00")
    repo.write("f.py", "2\n"); repo.commit('Revert "Add turbo mode"', date="2020-01-11T00:00:00+00:00")
    (s,) = find_revert_souls(read_history(repo.path))
    assert (s.kind, s.name, s.lifespan_days) == ("revert", "Add turbo mode", 10)

def test_revert_without_original_is_skipped(repo):
    repo.write("f.py", "1\n"); repo.commit('Revert "something from another branch"')
    assert find_revert_souls(read_history(repo.path)) == []

def test_quiet_contributor(repo):
    for i in range(5):
        repo.write("a.py", f"{i}\n"); repo.commit(f"ana {i}", author="Ana <ana@x>", date=f"2020-01-0{i+1}T00:00:00+00:00")
    repo.write("a.py", "z\n"); repo.commit("still here", author="Bo <bo@x>", date="2022-01-01T00:00:00+00:00")
    (s,) = find_quiet_contributors(read_history(repo.path))
    assert (s.name, s.touches, s.last_words) == ("Ana", 5, "ana 4")

def test_drive_by_contributor_ignored(repo):
    repo.write("a.py", "1\n"); repo.commit("one", author="Cy <cy@x>", date="2019-01-01T00:00:00+00:00")
    repo.write("a.py", "2\n"); repo.commit("late", date="2022-01-01T00:00:00+00:00")
    assert find_quiet_contributors(read_history(repo.path)) == []
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_souls.py -v`. Expected: the 4 new tests FAIL.
- [ ] **Step 3: Implement both functions.** For a revert, the original is the latest commit *before* the revert whose subject equals the captured group exactly.
- [ ] **Step 4: Run** `.venv/bin/pytest -v`. Expected: all pass.
- [ ] **Step 5: Commit** `feat: revert souls and quiet contributors`

---

### Task 4: Ranking, ghost list, line counts, Altar

**Files:**
- Create: `ofrenda/rank.py`, `ofrenda/altar.py`, `tests/test_rank.py`

**Interfaces:**
- Consumes: `Soul` (Tasks 2–3), `run_git` (Task 1)
- Produces:
  - `score(soul: Soul) -> float` (formula from the Design section)
  - `select(souls: list[Soul], top: int = 8) -> list[Soul]` (quotas from the Design section, in the order files, reverts, contributors)
  - `ghosts(souls: list[Soul], limit: int = 5) -> list[Soul]`
  - `enrich_lines(repo: Path, souls: list[Soul]) -> None`, which sets `lines_at_death` for file souls via `git cat-file -p <blob>`. A NUL in the first 8000 bytes means binary, so it is left as `None`. A `GitError` (missing blob in a partial or shallow clone) also leaves it as `None`.
  - `@dataclass Altar(repo_name: str, commit_count: int, first_date: datetime, last_date: datetime, souls: list[Soul], ghosts: list[Soul], verses: dict[str, tuple[str, str]], model: str | None)`. `verses` maps a soul id to `(verse, source)`, with `source` in `{"model","template"}`.

- [ ] **Step 1: Write the failing tests.** Use a `make_soul(**overrides)` helper in the test file.
  - `test_score_formula`: lifespan 300, touches 4, 2 authors, no return gives `10 + 8 + 6 == 24`, and with a return gives `49`.
  - `test_lifespan_capped`: lifespan 100000 contributes exactly `3650/30`.
  - `test_select_quotas`: 20 files, 5 reverts and 5 contributors with `top=8` give lengths 8, 3 and 3 by kind, files sorted by descending score.
  - `test_ghosts_exact_first`: an exact return outranks a same-name return even with a lower score.
  - `test_enrich_lines` (uses `repo`): a deleted `"a\nb\nc\n"` file gives 3; a deleted file containing `b"\x00\x01"` gives `None`.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_rank.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** Sorting key: `(-score, -died.date.timestamp())`.
- [ ] **Step 4: Run** `.venv/bin/pytest -v`. Expected: all pass.
- [ ] **Step 5: Commit** `feat: rank souls and count lines at death`

---

### Task 5: Calavera writer (Ollama + fallback + cache)

**Files:**
- Create: `ofrenda/calavera.py`, `tests/test_calavera.py`

**Interfaces:**
- Consumes: `Soul`
- Produces:
  - `fallback_verse(soul: Soul) -> str`
  - `clean_verse(raw: str) -> str | None`
  - `build_prompt(soul: Soul, lang: str) -> str`
  - `class CalaveraWriter(model: str, host: str = "http://127.0.0.1:11434", lang: str = "en", timeout: float = 90, cache_path: Path | None = None)` with `.write(soul: Soul) -> tuple[str, str]` (verse and source `"model"`/`"template"`) and `.offline_reason: str | None`

**Exact copy.** The fallback template, where `{lifespan}` is `lifespan_days`:
```
Here lies {name}, who lived {lifespan} days,
touched {touches} times in {len(authors)} people's ways.
"{last_words}" was all it said —
now marigolds bloom where its code once read.
```

**Exact copy.** The prompt (`{facts}` is one `key: value` line per fact: kind, name, born date and author, died date and author, last words, lifespan days, touches, authors, former names, returned):
```
You write a calavera literaria: a short, playful, affectionate Día de los Muertos
verse that mourns something as if it had died. Write exactly 4 rhyming lines in
{language}. Use ONLY these facts; do not invent numbers, people, or events.
Never be cruel about people. No title, no explanation, just the 4 lines.

{facts}
```
`{language}` is `English` or `Spanish`.

- [ ] **Step 1: Write the failing tests.** Fake Ollama with a `http.server` thread on port 0 in the test file.
  - `test_clean_verse_strips_wrapping`: input `"<think>hmm</think>\n```\n\"Line one\nLine two\n\nLine three\nLine four\"\n```"` gives `"Line one\nLine two\nLine three\nLine four"` (removes think blocks, fences and wrapping quotes; keeps ≤ 6 non-empty lines, each truncated to 120 characters).
  - `test_clean_verse_rejects_short`: `"ok"` gives `None`.
  - `test_clean_verse_strips_ansi`: `"\x1b[31mred\x1b[0m line\nsecond line"` contains no `\x1b`.
  - `test_writer_uses_model`: the fake server returns `{"response": "a\nb\nc\nd"}`, so the result is `("a\nb\nc\nd", "model")`. Assert the request JSON has `"stream": false`, `"think": false` and the right model.
  - `test_unreachable_host_falls_back_once`: pointing the host at a closed port and calling `.write` 3 times gives 3 `"template"` results. Monkeypatch `urllib.request.urlopen` to count calls, and assert exactly 1 call. `offline_reason` is set.
  - `test_model_missing_404_falls_back`: the fake server returns 404 `{"error":"model not found"}`, so the result is `"template"` and `offline_reason` contains `"model not found"`.
  - `test_cache_hit_skips_network` (uses `tmp_path`): a second writer with the same cache path does not call the server.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_calavera.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - POST `{host}/api/generate` with `{"model", "prompt", "stream": false, "think": false, "options": {"temperature": 0.8, "num_predict": 220}}`.
  - Any `URLError`, timeout, HTTP error, bad JSON, or a `clean_verse` result of `None` falls back to the template.
  - A connection or HTTP error sets `offline_reason` and disables further calls. Bad output only falls back for that one soul.
  - Cache JSON is keyed `f"{model}|{lang}|{soul.id}"` and stores model output only. Write it atomically (temp file plus `os.replace`).
- [ ] **Step 4: Run** `.venv/bin/pytest -v`. Expected: all pass.
- [ ] **Step 5: Smoke-test the real model** with `.venv/bin/python -c` on a hand-made Soul, using `CalaveraWriter("gemma4:e2b")`. Expected: 4 plausible lines in under ~15 s. If the output is often bad, tune *only* the prompt wording and record what changed in the commit message.
- [ ] **Step 6: Commit** `feat: local calavera writer with fallback`

---

### Task 6: Terminal altar

**Files:**
- Create: `ofrenda/render_terminal.py`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `Altar` (Task 4)
- Produces: `render_terminal(altar: Altar, console: Console) -> None`

**Layout:**
- Banner: `🕯️  OFRENDA · {repo_name}  🕯️`, a row of `🌼`, and a subtitle `{commit_count} commits · {first_date:%Y} – {last_date:%Y}`.
- If there are ghosts, a `👻 They came back` panel, one line per ghost: `{name} → {returned.path} ({"exact same content" if exact else "same name, new body"}) · {returned.commit.date:%Y-%m-%d}`.
- The souls as `Panel`s in `Columns`. Each card has the name as title, then fact lines: `born` (date and author), `died` (date and author), `lifespan`, `touches`, `lines at death` (omitted if None), `once known as` (omitted if empty), `last words "…"`. Then a rule, the verse in italic, and the dim source label from Global Constraints.
- Footer: `facts from git · verses by {model} on this machine` (`verses from a template` when the model was offline).

Colors: marigold `#F2A007`, magenta `#D6336C`, violet `#7048E8`.

- [ ] **Step 1: Write the failing tests.** Use `Console(record=True, width=100, color_system=None)` and `export_text()`.
  - `test_terminal_shows_facts_and_label`: output contains the soul name, `"remove legacy"`, `"calavera · written locally by gemma4:e2b"` and `"👻 They came back"` when ghosts are present.
  - `test_terminal_escapes_markup`: a soul named `"[bold red]x[/] .py"` shows literally (wrap every dynamic string in `rich.text.Text` or `rich.markup.escape`).
  - `test_terminal_empty_altar`: no souls prints `"Nobody has died here. Yet."`
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_render.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `.venv/bin/pytest -v`. Expected: all pass.
- [ ] **Step 5: Commit** `feat: terminal altar`

---

### Task 7: HTML altar

**Files:**
- Create: `ofrenda/render_html.py`
- Modify: `tests/test_render.py`

**Interfaces:**
- Produces: `render_html(altar: Altar) -> str` (a complete document)

**Design:**
- One self-contained page with inline CSS, no JS and no external URLs.
- Dark background `#1a1024`, a papel picado banner (a CSS row of colored triangles via `clip-path`), and a candle flame with a CSS flicker animation that is disabled under `prefers-reduced-motion`.
- Cards in a CSS grid (`minmax(260px, 1fr)`) with the same content as Task 6; ghost cards get a translucent "spectral" style.
- `<title>Ofrenda · {repo_name}</title>`. Responsive down to 360 px wide.

- [ ] **Step 1: Write the failing tests**
  - `test_html_escapes_everything`: a soul named `<script>alert(1)</script>.js` with last words `"a & b"` must give output without `<script>alert` and containing `&lt;script&gt;` and `a &amp; b`.
  - `test_html_is_offline`: the output contains none of `http://`, `https://` or `//cdn`.
  - `test_html_has_label`: the output contains the source label text.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_render.py -v`. Expected: the 3 new tests FAIL.
- [ ] **Step 3: Implement.** Run *every* dynamic value through `html.escape(str(v), quote=True)`. Build the page with f-strings or `string.Template` (no Jinja; dependency limit).
- [ ] **Step 4: Run** `.venv/bin/pytest -v`. Expected: all pass. Open the output in a browser once and look at it.
- [ ] **Step 5: Commit** `feat: html altar`

---

### Task 8: CLI wiring (`git ofrenda`)

**Files:**
- Create: `ofrenda/cli.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: everything above
- Produces: `main(argv: list[str] | None = None) -> int` and `run() -> None` (`sys.exit(main())`)

**Arguments:**

| argument | default |
|---|---|
| `path` | `.` |
| `--top N` | 8 |
| `--model M` | `$OFRENDA_MODEL` or `gemma4:e2b` |
| `--host URL` | `http://127.0.0.1:11434` |
| `--lang {en,es}` | `en` |
| `--no-ai` | off; template verses only, no network |
| `--include-people` | off; enables contributor souls |
| `--quiet-days N` | 365 |
| `--ignore PATTERN` | repeatable |
| `--html PATH` | none |

**Flow:**
1. `read_history`
2. find the souls
3. `select` and `ghosts`
4. `enrich_lines`
5. write the verses for the selected and ghost souls, behind a rich `status` spinner showing `lighting candles for {name}…`
6. build the `Altar` and render it to the terminal
7. if `--html` was given, write the file and print its path

When `offline_reason` gets set, print one dim warning line: `model offline ({reason}); using template verses`.

**Exit codes and messages:**
- Not a repo: stderr `ofrenda: {path} is not a git repository`, exit 2.
- No commits: `No history yet — nothing has died.`, exit 0.
- Shallow repo: print a warning line `shallow clone: older history is missing; run git fetch --unshallow for the full altar`, then continue.

- [ ] **Step 1: Write the failing tests.** Use `capsys` and the `repo` fixture, always with `--no-ai`.
  - `test_cli_not_a_repo_exit_2`
  - `test_cli_empty_repo_exit_0`
  - `test_cli_renders_soul`: a deleted file's name appears in stdout and the return value is 0.
  - `test_cli_writes_html`: `--html out.html` creates the file, which contains the soul name.
  - `test_cli_no_ai_makes_no_network_calls`: monkeypatch `urllib.request.urlopen` to raise, and the run still returns 0.
  - `test_cli_people_opt_in`: the quiet contributor's name is absent without `--include-people` and present with it.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_cli.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `.venv/bin/pytest -v`. Expected: all pass. Then reinstall and run it for real: `.venv/bin/pip install -e . && PATH=$PWD/.venv/bin:$PATH git ofrenda .` should print an altar for this repo.
- [ ] **Step 5: Run it against a big real repo** to check performance: `git clone https://github.com/expressjs/express /tmp/express && git ofrenda /tmp/express --top 8`. Expected: the history pass takes under 10 s and the whole run (8–13 verses) under ~3 min. If parsing is slow, profile before changing anything.
- [ ] **Step 6: Commit** `feat: git ofrenda CLI`

---

### Task 9: README, demo, DEV post

**Files:**
- Create: `README.md`, `docs/demo.gif` (or a link to the video), `docs/ofrenda-express.html` (sample output)

- [ ] **Step 1: Write the README.** Cover what the tool is (one paragraph), install (`pipx install git+…` or `pip install -e .`, then `ollama pull gemma4:e2b`), usage examples for every flag, a "facts vs verses" note, a privacy note (nothing leaves the machine), and the model swap (`--model gemma3:4b-it-q4_K_M`, `--model qwen2.5-coder:7b`).
- [ ] **Step 2: Record the demo.** A 30–60 s screen recording of `git ofrenda` on express: the altar fills in, the ghost panel appears, then the HTML page opens. Also run with two different models side by side to show the swap.
- [ ] **Step 3: Draft the DEV post** using the challenge's submission template, with its sections in this order:
  1. What I Built
  2. Demo (the video, plus a hosted copy of the sample HTML altar if possible)
  3. Code (the repo link)
  4. How I Built It: one git pass, blob-hash ghosts, facts vs verse, and Gemma 4 E2B running locally through Ollama (`think: false`)
  5. **Why Does Open Innovation Matter?**: private history stays local, works offline, a one-flag model swap, $0 on 2,000-commit repos; where it beat a closed API (latency is irrelevant, privacy is decisive, no API key for a CLI user)
  6. My Agent Session (optional)
  7. The Spirit of It (optional): Día de los Muertos, calaveras literarias
  8. Prize Categories: **Gemma**

  Close with what's next: function-level souls via tree-sitter, removed dependencies, a `--date 11-02` mode.

  Disclose AI assistance as DEV's rules require.
- [ ] **Step 4: Push to a public GitHub repo** (confirm with the user first). Add a license (MIT).
- [ ] **Step 5: Publish the post before 2026-10-31 23:59 PDT.** Use tags `#devchallenge #hf26challenge` (the template adds them). If anything is committed after the deadline, note it in the README.

---

## Out of scope (this deadline)

- Function-level souls (tree-sitter)
- Removed dependencies
- Deleted branches and reflog
- A web server
- Images or audio
- Spanish UI chrome (the verse can be Spanish via `--lang es`; the labels stay English)

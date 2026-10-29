from datetime import UTC, datetime

from ofrenda.history import Change, Commit, Entry, read_history
from ofrenda.souls import (
    DEFAULT_IGNORES, find_file_souls, find_quiet_contributors, find_revert_souls, is_ignored,
)


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

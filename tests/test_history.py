import pytest

from ofrenda.git import GitError
from ofrenda.history import read_history


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

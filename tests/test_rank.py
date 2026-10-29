from datetime import UTC, datetime, timedelta

from ofrenda.history import Commit, read_history
from ofrenda.rank import enrich_lines, ghosts, score, select
from ofrenda.souls import Return, Soul, find_file_souls

T0 = datetime(2020, 1, 1, tzinfo=UTC)


def make_soul(lifespan=300, touches=4, authors=("Ana", "Bo"), kind="file",
              returned=None, died_offset=0, name="x.py", **overrides):
    born = Commit("a" * 40, "Ana", "a@x", T0, "born")
    died = Commit("b" * 40, "Bo", "b@x", T0 + timedelta(days=lifespan + died_offset), "die")
    if died_offset:
        born = Commit("a" * 40, "Ana", "a@x", T0 + timedelta(days=died_offset), "born")
    fields = dict(id=f"{kind}:{name}:{lifespan}:{touches}:{died_offset}", kind=kind, name=name,
                  born=born, died=died, last_words="die", touches=touches,
                  authors=list(authors), returned=returned)
    fields.update(overrides)
    return Soul(**fields)


def test_score_formula():
    assert score(make_soul()) == 24
    back = Return(Commit("c" * 40, "Cy", "c@x", T0, "back"), "x.py", exact=False)
    assert score(make_soul(returned=back)) == 49


def test_lifespan_capped():
    s = make_soul(lifespan=100000, touches=0, authors=())
    assert score(s) == 3650 / 30


def test_select_quotas():
    files = [make_soul(lifespan=10 * i, name=f"f{i}.py") for i in range(20)]
    reverts = [make_soul(kind="revert", lifespan=i, name=f"r{i}") for i in range(5)]
    people = [make_soul(kind="contributor", touches=i, name=f"p{i}") for i in range(5)]
    chosen = select(files + reverts + people, top=8)
    by_kind = [s.kind for s in chosen]
    assert (by_kind.count("file"), by_kind.count("revert"), by_kind.count("contributor")) == (8, 3, 3)
    assert by_kind == ["file"] * 8 + ["revert"] * 3 + ["contributor"] * 3
    picked = [s for s in chosen if s.kind == "file"]
    assert [score(s) for s in picked] == sorted((score(s) for s in picked), reverse=True)
    assert picked[0].name == "f19.py"
    assert [s.name for s in chosen if s.kind == "revert"] == ["r4", "r3", "r2"]
    assert [s.name for s in chosen if s.kind == "contributor"] == ["p4", "p3", "p2"]


def test_ghosts_exact_first():
    c = Commit("c" * 40, "Cy", "c@x", T0 + timedelta(days=5000), "back")
    exact = make_soul(lifespan=1, touches=1, name="low.py", returned=Return(c, "a", exact=True))
    named = make_soul(lifespan=3000, touches=50, name="high.py", returned=Return(c, "b", exact=False))
    plain = make_soul(name="dead.py")
    assert [s.name for s in ghosts([named, plain, exact])] == ["low.py", "high.py"]


def test_enrich_lines(repo):
    repo.write("text.txt", "a\nb\nc\n"); repo.write("blob.bin", b"\x00\x01"); repo.commit("born")
    repo.delete("text.txt"); repo.delete("blob.bin"); repo.commit("die")
    souls = find_file_souls(read_history(repo.path))
    enrich_lines(repo.path, souls)
    lines = {s.name: s.lines_at_death for s in souls}
    assert lines == {"text.txt": 3, "blob.bin": None}


def test_enrich_lines_missing_blob_is_none(repo):
    repo.write("a.txt", "x\n"); repo.commit("born")
    s = make_soul(blob="d" * 40)
    enrich_lines(repo.path, [s])
    assert s.lines_at_death is None


def test_ghosts_skip_same_day_moves_and_rank_by_time_gone():
    def back(days_after_death, lifespan=300):
        return Commit("c" * 40, "Cy", "c@x", T0 + timedelta(days=lifespan + days_after_death), "back")
    move = make_soul(name="moved.py", returned=Return(back(0), "new/moved.py", exact=True))
    short = make_soul(name="short.py", returned=Return(back(3), "short.py", exact=True))
    long = make_soul(name="long.py", returned=Return(back(900), "long.py", exact=True))
    assert [s.name for s in ghosts([move, short, long])] == ["long.py", "short.py"]

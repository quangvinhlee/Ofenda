import urllib.request

from ofrenda.cli import main


def bury_a_file(repo):
    repo.write("ghost_town.py", "boo\n"); repo.commit("born", date="2020-01-01T00:00:00+00:00")
    repo.delete("ghost_town.py"); repo.commit("remove ghost town", date="2021-01-01T00:00:00+00:00")


def test_cli_not_a_repo_exit_2(tmp_path, capsys):
    assert main([str(tmp_path), "--no-ai"]) == 2
    assert "is not a git repository" in capsys.readouterr().err


def test_cli_empty_repo_exit_0(repo, capsys):
    assert main([str(repo.path), "--no-ai"]) == 0
    assert "No history yet — nothing has died." in capsys.readouterr().out


def test_cli_renders_soul(repo, capsys):
    bury_a_file(repo)
    assert main([str(repo.path), "--no-ai"]) == 0
    out = capsys.readouterr().out
    assert "ghost_town.py" in out and "calavera · template (model offline)" in out


def test_cli_writes_html(repo, tmp_path, capsys):
    bury_a_file(repo)
    out_file = tmp_path / "out.html"
    assert main([str(repo.path), "--no-ai", "--html", str(out_file)]) == 0
    assert "ghost_town.py" in out_file.read_text(encoding="utf-8")
    assert str(out_file) in capsys.readouterr().out


def test_cli_no_ai_makes_no_network_calls(repo, monkeypatch, capsys):
    bury_a_file(repo)

    def boom(*a, **kw):
        raise AssertionError("network call with --no-ai")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert main([str(repo.path), "--no-ai"]) == 0


def test_cli_people_opt_in(repo, capsys):
    for i in range(5):
        repo.write("a.py", f"{i}\n"); repo.commit(f"zed {i}", author="Zed Quiet <zed@x>", date=f"2020-01-0{i+1}T00:00:00+00:00")
    repo.write("a.py", "z\n"); repo.commit("still here", date="2022-01-01T00:00:00+00:00")
    assert main([str(repo.path), "--no-ai"]) == 0
    assert "Zed Quiet" not in capsys.readouterr().out
    assert main([str(repo.path), "--no-ai", "--include-people"]) == 0
    assert "Zed Quiet" in capsys.readouterr().out


def test_cli_offline_model_warns_once_and_falls_back(repo, capsys):
    bury_a_file(repo)
    repo.write("second.py", "2\n"); repo.commit("born 2")
    repo.delete("second.py"); repo.commit("die 2")
    assert main([str(repo.path), "--host", "http://127.0.0.1:9", "--model", "nope"]) == 0
    out = capsys.readouterr().out
    assert out.count("using template verses") == 1 and "model offline (" in out
    assert "calavera · template (model offline)" in out


def test_cli_never_writes_to_working_tree(repo, capsys):
    bury_a_file(repo)
    before = sorted(p.name for p in repo.path.iterdir())
    assert main([str(repo.path), "--host", "http://127.0.0.1:9"]) == 0
    assert sorted(p.name for p in repo.path.iterdir()) == before


def test_cli_shows_census(repo, capsys):
    bury_a_file(repo)
    assert main([str(repo.path), "--no-ai"]) == 0
    out = capsys.readouterr().out
    assert "Graveyard census" in out and "deleted files" in out

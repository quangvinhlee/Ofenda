import json
import socket
import threading
import urllib.request
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from ofrenda.calavera import CalaveraWriter, build_prompt, clean_verse, fallback_verse
from ofrenda.history import Commit
from ofrenda.souls import Soul

MODEL = "gemma4:e2b"


def make_soul(**overrides) -> Soul:
    born = Commit("a" * 40, "Ana", "a@x", datetime(2020, 1, 1, tzinfo=UTC), "born")
    died = Commit("b" * 40, "Bo", "b@x", datetime(2021, 1, 1, tzinfo=UTC), "remove legacy")
    fields = dict(id="file:old.py:bbbbbbbbbbbb", kind="file", name="old.py", born=born,
                  died=died, last_words="remove legacy", touches=3, authors=["Ana", "Bo"])
    fields.update(overrides)
    return Soul(**fields)


class FakeOllama:
    def __init__(self, status=200, body=None):
        self.status = status
        self.body = body if body is not None else {"response": "a\nb\nc\nd"}
        self.requests: list[dict] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["Content-Length"])
                fake.requests.append(json.loads(self.rfile.read(length)))
                payload = json.dumps(fake.body).encode()
                self.send_response(fake.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.host = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def ollama():
    servers: list[FakeOllama] = []

    def start(**kw) -> FakeOllama:
        servers.append(FakeOllama(**kw))
        return servers[-1]

    yield start
    for s in servers:
        s.close()


def closed_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_clean_verse_strips_wrapping():
    raw = "<think>hmm</think>\n```\n\"Line one\nLine two\n\nLine three\nLine four\"\n```"
    assert clean_verse(raw) == "Line one\nLine two\nLine three\nLine four"


def test_clean_verse_rejects_short():
    assert clean_verse("ok") is None


def test_clean_verse_strips_ansi():
    assert "\x1b" not in clean_verse("\x1b[31mred\x1b[0m line\nsecond line")


def test_clean_verse_caps_lines_and_width():
    out = clean_verse("\n".join(["x" * 200] * 10))
    lines = out.split("\n")
    assert len(lines) == 6 and all(len(l) == 120 for l in lines)


def test_fallback_verse_is_exact_copy():
    assert fallback_verse(make_soul()) == (
        "Here lies old.py, who lived 366 days,\n"
        "touched 3 times in 2 people's ways.\n"
        '"remove legacy" was all it said —\n'
        "now marigolds bloom where its code once read."
    )


def test_prompt_has_facts_and_language():
    p = build_prompt(make_soul(), "es")
    assert "exactly 4 rhyming lines in\nSpanish." in p
    assert "name: old.py" in p and "lifespan days: 366" in p and "last words: remove legacy" in p


def test_prompt_keeps_people_ungendered():
    assert 'never "he" or "she"' in build_prompt(make_soul(kind="contributor"), "en")


def test_writer_uses_model(ollama):
    srv = ollama()
    w = CalaveraWriter(MODEL, host=srv.host)
    assert w.write(make_soul()) == ("a\nb\nc\nd", "model")
    (req,) = srv.requests
    assert req["stream"] is False and req["think"] is False and req["model"] == MODEL


def test_unreachable_host_falls_back_once(monkeypatch):
    calls = []
    real = urllib.request.urlopen

    def counting(*a, **kw):
        calls.append(1)
        return real(*a, **kw)

    monkeypatch.setattr(urllib.request, "urlopen", counting)
    w = CalaveraWriter(MODEL, host=f"http://127.0.0.1:{closed_port()}", timeout=2)
    results = [w.write(make_soul(id=f"s{i}")) for i in range(3)]
    assert [src for _, src in results] == ["template"] * 3
    assert len(calls) == 1
    assert w.offline_reason


def test_model_missing_404_falls_back(ollama):
    srv = ollama(status=404, body={"error": "model not found"})
    w = CalaveraWriter(MODEL, host=srv.host)
    assert w.write(make_soul())[1] == "template"
    assert "model not found" in w.offline_reason


def test_bad_output_falls_back_for_that_soul_only(ollama):
    srv = ollama(body={"response": "ok"})
    w = CalaveraWriter(MODEL, host=srv.host)
    assert w.write(make_soul())[1] == "template"
    assert w.offline_reason is None
    srv.body = {"response": "a\nb\nc\nd"}
    assert w.write(make_soul(id="other"))[1] == "model"


def test_cache_hit_skips_network(ollama, tmp_path):
    srv = ollama()
    cache = tmp_path / "cache" / "calaveras.json"
    assert CalaveraWriter(MODEL, host=srv.host, cache_path=cache).write(make_soul())[1] == "model"
    again = CalaveraWriter(MODEL, host=srv.host, cache_path=cache).write(make_soul())
    assert again == ("a\nb\nc\nd", "model")
    assert len(srv.requests) == 1

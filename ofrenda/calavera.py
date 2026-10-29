"""Calaveras literarias: a local model writes the verse, a template stands in when it can't."""

import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from .souls import Soul

_PROMPT = """You write a calavera literaria: a short, playful, affectionate Día de los Muertos
verse that mourns something as if it had died. Write exactly 4 rhyming lines in
{language}. Use ONLY these facts; do not invent numbers, people, or events.
Never be cruel about people. No title, no explanation, just the 4 lines.
Name it by its name and work in at least one of the facts.
If the kind is contributor, the person is alive and only went quiet: say so gently,
and refer to them by name or as "they", never "he" or "she".

{facts}"""

_LANGUAGES = {"en": "English", "es": "Spanish"}

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b[@-_]")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_QUOTES = "\"'“”‘’`"

MAX_LINES = 6
MAX_WIDTH = 120


def fallback_verse(soul: Soul) -> str:
    return (
        f"Here lies {soul.name}, who lived {soul.lifespan_days} days,\n"
        f"touched {soul.touches} times in {len(soul.authors)} people's ways.\n"
        f'"{soul.last_words}" was all it said —\n'
        f"now marigolds bloom where its code once read."
    )


def clean_verse(raw: str) -> str | None:
    """Strip model wrapping (think blocks, fences, quotes, escapes); None if too little is left."""
    text = _THINK.sub("", raw)
    text = _ANSI.sub("", text)
    lines = [line.strip() for line in text.splitlines()]
    lines = [_CONTROL.sub("", line) for line in lines if line and not line.startswith("```")]
    if lines:
        lines[0] = lines[0].lstrip(_QUOTES).strip()
        lines[-1] = lines[-1].rstrip(_QUOTES).strip()
    lines = [line[:MAX_WIDTH] for line in lines if line][:MAX_LINES]
    return "\n".join(lines) if len(lines) >= 2 else None


def _returned_fact(soul: Soul) -> str:
    r = soul.returned
    if r is None:
        return "no"
    how = "exact same content" if r.exact else "same name, new content"
    return f"yes, as {r.path} on {r.commit.date:%Y-%m-%d} ({how})"


def build_prompt(soul: Soul, lang: str) -> str:
    facts = {
        "kind": soul.kind,
        "name": soul.name,
        "born": f"{soul.born.date:%Y-%m-%d} by {soul.born.author}",
        "died": f"{soul.died.date:%Y-%m-%d} by {soul.died.author}",
        "last words": soul.last_words,
        "lifespan days": soul.lifespan_days,
        "touches": soul.touches,
        "authors": ", ".join(soul.authors) or "unknown",
        "former names": ", ".join(soul.former_names) or "none",
        "returned": _returned_fact(soul),
    }
    lines = "\n".join(f"{k}: {v}" for k, v in facts.items())
    return _PROMPT.format(language=_LANGUAGES.get(lang, "English"), facts=lines)


class CalaveraWriter:
    def __init__(self, model: str, host: str = "http://127.0.0.1:11434", lang: str = "en",
                 timeout: float = 90, cache_path: Path | None = None):
        self.model = model
        self.host = host.rstrip("/")
        self.lang = lang
        self.timeout = timeout
        self.cache_path = cache_path
        self.offline_reason: str | None = None
        self._cache: dict[str, str] = self._load_cache()

    def write(self, soul: Soul) -> tuple[str, str]:
        key = f"{self.model}|{self.lang}|{soul.id}"
        if key in self._cache:
            return self._cache[key], "model"
        if self.offline_reason is None:
            verse = self._generate(soul)
            if verse is not None:
                self._cache[key] = verse
                self._save_cache()
                return verse, "model"
        return fallback_verse(soul), "template"

    def _generate(self, soul: Soul) -> str | None:
        body = json.dumps({
            "model": self.model,
            "prompt": build_prompt(soul, self.lang),
            "stream": False,
            "think": False,
            "options": {"temperature": 0.8, "num_predict": 220},
        }).encode()
        req = urllib.request.Request(f"{self.host}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            self.offline_reason = f"HTTP {e.code}: {_error_text(e)}"
            return None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            self.offline_reason = str(getattr(e, "reason", e)) or type(e).__name__
            return None
        try:
            return clean_verse(json.loads(raw)["response"])
        except (ValueError, KeyError, TypeError):
            return None

    def _load_cache(self) -> dict[str, str]:
        if self.cache_path is None:
            return {}
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return {k: v for k, v in data.items() if isinstance(v, str)} if isinstance(data, dict) else {}

    def _save_cache(self) -> None:
        if self.cache_path is None:
            return
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.cache_path.parent, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.cache_path)
        except OSError:
            pass  # a cache we can't write is only a slower next run


def _error_text(e: urllib.error.HTTPError) -> str:
    try:
        return json.loads(e.read())["error"]
    except (ValueError, KeyError, TypeError, OSError):
        return e.reason or "error"

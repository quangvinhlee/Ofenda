---
title: "git ofrenda: a Día de los Muertos altar for everything your repo ever deleted"
published: false
tags: devchallenge, hf26challenge, opensource, ai
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge: Ghost in the Machine](https://dev.to/challenges/hacktoberfest-week4-2026-10-26).*

## What I Built

Every repository is a graveyard. Files get deleted, features get reverted, and people who
once committed every day go quiet. On Día de los Muertos you build an *ofrenda*, an altar,
so the dead are remembered. So I built one for git.

`git ofrenda` reads a repository's entire history and puts its dead on an altar:

- **deleted files**, with their whole life story followed through renames: when they were
  born, who touched them, how many lines they had when they died, and their last words
  (the commit message that killed them);
- **reverted commits**, linked back to the commit they undid;
- **contributors who went quiet** (opt-in, and gentle: they're alive, just quiet);
- and **ghosts**: deleted files that came back from the dead.

For each soul, Gemma, running locally, writes a *calavera literaria*, the short satirical
memorial verse that Mexican newspapers have printed every November since the 1800s.

<!-- TODO before publishing: embed the demo video, e.g. {% embed https://youtu.be/... %} -->

## Demo

<!-- TODO: 30–60 s recording: `git ofrenda ~/src/express --include-people --html altar.html`,
the cards filling in, the ghost panel, then the HTML altar in a browser, then the same run
with `--model gemma3:4b-it-q4_K_M` to show the swap. -->

Here is the altar for [expressjs/express](https://github.com/expressjs/express): 6,183
commits from 2009 to 2026. The whole history pass takes **0.11 s**, and a cold full run,
including 16 verses from Gemma on my laptop, takes about 9 s (3 s once the verses are cached).

![The altar for express](https://raw.githubusercontent.com/quangvinhlee/Ofenda/main/docs/altar-express.svg)

Some of who's on it:

- `bin/express` lived 1,276 days and 148 commits. Its last words: *"remove binary"*.
- `.travis.yml` lived almost ten years (3,506 days) before *"build: use GitHub Actions
  instead of Travis CI"*.
- `docs/guide.md` was 1,366 lines long when *"removed old docs"* took it.

And the ghost I didn't expect: `test/app.options.js` was deleted in 2012 and came back
**321 days later with byte-for-byte identical content**, through a commit titled
`Revert "remove old OPTIONS default response"`.

```text
lib/router/index.js
  born           2011-04-25 · Tj Holowaychuk
  died           2015-07-06 · Douglas Christopher Wilson
  lifespan       1533 days
  touches        133
  lines at death 626
  once known as  lib/router.js
  last words     "Use router module for routing"
  ────────────────────────────────────────────
  File, in slumber deep and still,
  Its coding journey to its end,
  A quiet pause upon the hill,
  Where former paths now softly bend.
  calavera · written locally by gemma4:e2b
```

## Code

{% github quangvinhlee/Ofenda %}

## How I Built It

**One pass over history.** `git log --raw -z --no-abbrev -M` gives every commit with every
file change, its blob hashes and its renames, NUL-separated so filenames with spaces,
unicode or newlines survive. A single forward pass keeps a "living" table of files, follows
renames so `lib/router.js → lib/router/index.js` is one life rather than two, and moves each
deleted file to a graveyard.

**Ghosts are proven, not guessed.** Git names file contents by their hash. When a later
commit adds a blob whose hash equals a dead file's last blob, it's the same file, byte for
byte, back from the grave. Two traps I hit along the way:

- every empty `__init__.py` and `.gitkeep` has the same hash, so the empty blob never
  counts as a resurrection;
- in express's early history, half the "ghosts" were files deleted in one commit and
  re-added the same day in the next, which is a move, not a haunting. Returns less than a
  day after death don't count.

**Facts from git, verses from the model.** This is the rule the whole design hangs on.
Every number on a card comes from git. Gemma gets those facts as `key: value` lines and is
told to write exactly four rhyming lines using *only* those facts and never to be cruel
about people. Every verse is labelled with its source, so you always know which parts are
data and which are poetry.

**Gemma 4, locally, through Ollama.** I tested both Gemma models I had pulled.
`gemma4:e2b` wrote clearly better verses than `gemma3:4b`, which liked to read "1961 days"
as "nineteen sixty-one". One gotcha: Gemma 4 is a thinking model, and with a 220-token
budget it spent every token thinking and returned an empty string. Sending
`"think": false` fixed it, and each verse now takes about 0.3 s on a laptop.

I also tuned the prompt after a smoke test. In the first draft Gemma gave a contributor a
gender from their name alone and mourned them as if they had actually died. Now the prompt
says a quiet contributor is alive and just went quiet, and to call people by name or
"they".

**It degrades gracefully.** If Ollama is down or the model isn't pulled, you get one warning
line and template verses. It never waits out a timeout once per soul. Model verses are
cached in `.git/ofrenda/`, and the tool never touches your working tree. Commit messages and
filenames are untrusted input, so terminal output is stripped of escape sequences and the
HTML escapes everything. A file named `<script>alert(1)</script>.js` is just a sad file.

**Stack:** Python, the `git` CLI, [`rich`](https://github.com/Textualize/rich) for the
terminal altar, and plain `urllib` to talk to Ollama (no SDK). The HTML altar is a single
self-contained page: papel picado made from CSS `clip-path`, candle flames that flicker
(but not under `prefers-reduced-motion`), and no external requests at all. 58 tests,
written test-first.

## Why Does Open Innovation Matter?

Because of what this tool reads. A repository's *deleted* history is where the things you
didn't want to keep live: the config file with the old API key, the half-finished feature,
the code a client never saw. A tool that ships all of that to a hosted API to get a poem
back is a bad deal. With an open-weight model on my own machine:

- **private history stays private**: nothing leaves the laptop, and with `--no-ai` there's
  no network at all;
- **it works offline**, on a plane or behind a corporate proxy;
- **it costs nothing**: express has 6,183 commits, and running this on every repo I own
  costs $0, with no API key to set up for a CLI user;
- **the model is a flag**: `--model gemma3:4b-it-q4_K_M`, `--model qwen2.5-coder:7b`, or
  whatever comes out next month. Open weights mean the tool isn't hostage to one vendor's
  pricing or deprecation schedule.

Latency, the usual argument for a big hosted model, doesn't matter here: a small local
model writes a verse in a third of a second. Privacy is what decides it.

## The Spirit of It

Día de los Muertos isn't sad. It's remembering with affection and a bit of humor, which is
exactly how developers talk about the code they deleted. The *calaveras literarias* have
always teased the living as if they were already dead. Here they tease files, which can
take it. `git ofrenda` is also a strangely good way to learn a codebase's story: who built
what, what got rewritten, and what refused to stay dead.

## Prize Categories

- **Gemma**: every verse is written by Gemma 4 (`gemma4:e2b`) running locally through Ollama.

---

*AI disclosure: I built this with help from an AI coding assistant (Claude Code), which
helped write the implementation, the tests and a draft of this post. The verses inside
the tool are written by Gemma, locally.*

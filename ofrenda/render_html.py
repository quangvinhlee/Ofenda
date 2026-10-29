"""The altar as one self-contained HTML page: inline CSS, no JS, no external URLs."""

import html

from .altar import Altar, clean_text, fact_rows, footer, ghost_line, source_label, subtitle
from .rank import is_ghost
from .souls import Soul

_PICADO_COLORS = ("#F2A007", "#D6336C", "#7048E8", "#2FB380", "#F76707", "#E64980")

_CSS = """
:root { --bg:#1a1024; --panel:#251733; --ink:#f6ecdf; --dim:#b9a6c9; --marigold:#F2A007;
        --magenta:#D6336C; --violet:#7048E8; --pumpkin:#F76707; }
* { box-sizing:border-box; }
html, body { margin:0; background:var(--bg); color:var(--ink); }
body { font:16px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
       min-height:100vh; overflow-x:hidden; }
.picado { display:flex; height:64px; }
.picado span { flex:1; clip-path:polygon(0 0, 100% 0, 100% 70%, 50% 100%, 0 70%);
               opacity:.9; margin:0 2px; }
header { text-align:center; padding:24px 16px 8px; }
h1 { margin:8px 0 4px; font-size:clamp(1.6rem, 5vw, 2.6rem); letter-spacing:.06em;
     color:var(--marigold); overflow-wrap:anywhere; }
.sub { color:var(--dim); margin:0; }
.marigolds { font-size:1.2rem; letter-spacing:.3em; margin:12px 0 0; overflow:hidden; white-space:nowrap; }
.candles { display:flex; justify-content:center; gap:40px; margin:20px 0 4px; }
.candle { position:relative; width:18px; height:46px; margin-top:22px; border-radius:3px;
          background:linear-gradient(#fff5e0, #e9d6b8); }
.flame { position:absolute; left:50%; top:-22px; width:14px; height:22px; margin-left:-7px;
         border-radius:50% 50% 50% 50% / 60% 60% 40% 40%;
         background:radial-gradient(circle at 50% 70%, #fff7c2 0 25%, #F2A007 55%, #D6336C 100%);
         box-shadow:0 0 18px 6px rgba(242,160,7,.45); transform-origin:50% 100%;
         animation:flicker 1.6s ease-in-out infinite alternate; }
.candle:nth-child(2) .flame { animation-delay:.4s; }
.candle:nth-child(3) .flame { animation-delay:.9s; }
@keyframes flicker { 0% { transform:scale(1) rotate(-2deg); opacity:.95; }
                     50% { transform:scale(1.08, .94) rotate(2deg); opacity:1; }
                     100% { transform:scale(.94, 1.06) rotate(-1deg); opacity:.85; } }
@media (prefers-reduced-motion: reduce) { .flame { animation:none; } }
main { max-width:1180px; margin:0 auto; padding:8px 16px 32px; }
h2 { color:var(--violet); font-size:1.15rem; margin:28px 0 10px; }
.ghosts { list-style:none; margin:0; padding:14px 16px; border:1px dashed var(--violet);
          border-radius:12px; background:rgba(112,72,232,.12); }
.ghosts li { overflow-wrap:anywhere; padding:3px 0; }
.grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:18px; }
.card { background:var(--panel); border:1px solid rgba(242,160,7,.55); border-top:4px solid var(--marigold);
        border-radius:12px; padding:16px; display:flex; flex-direction:column; min-width:0; }
.card.ghost { background:rgba(112,72,232,.16); border-color:rgba(160,140,255,.55);
              border-top-color:var(--violet); box-shadow:0 0 24px rgba(112,72,232,.35);
              backdrop-filter:blur(2px); }
.kind { text-align:center; font-size:.75rem; text-transform:uppercase; letter-spacing:.12em; color:var(--magenta); }
.card h3 { margin:2px 0 10px; font-size:1.05rem; font-family:ui-monospace, SFMono-Regular, Menlo, monospace;
           overflow-wrap:anywhere; }
dl { display:grid; grid-template-columns:auto 1fr; gap:2px 12px; margin:0; font-size:.9rem; }
dt { color:var(--dim); white-space:nowrap; }
dd { margin:0; overflow-wrap:anywhere; }
.verse { margin:14px 0 6px; padding-top:12px; border-top:1px solid var(--magenta);
         font-style:italic; white-space:pre-line; overflow-wrap:anywhere; }
.label { color:var(--dim); font-size:.78rem; margin-top:auto; }
.empty { text-align:center; color:var(--marigold); font-style:italic; font-size:1.3rem; margin:40px 0; }
footer { text-align:center; color:var(--dim); font-size:.85rem; padding:0 16px 32px; }
body { background:radial-gradient(ellipse at 50% -10%, #3b1f52 0, var(--bg) 55%) var(--bg) no-repeat; }
.sky { position:relative; height:0; }
.moon { position:absolute; right:8%; top:70px; width:64px; height:64px; border-radius:50%;
        background:radial-gradient(circle at 35% 35%, #fff8e1, #f3d9a4 60%, #d9b46a);
        box-shadow:0 0 40px 12px rgba(243,217,164,.35); }
.bat { position:absolute; top:90px; font-size:1.6rem; animation:fly 14s linear infinite; }
.bat.b2 { top:150px; font-size:1.1rem; animation-duration:19s; animation-delay:-7s; }
.bat.b3 { top:60px; font-size:1.3rem; animation-duration:23s; animation-delay:-13s; }
@keyframes fly { 0% { left:-8%; transform:translateY(0); } 25% { transform:translateY(-18px); }
                 50% { transform:translateY(10px); } 75% { transform:translateY(-12px); }
                 100% { left:104%; transform:translateY(0); } }
@media (prefers-reduced-motion: reduce) { .bat { animation:none; left:12%; } .bat.b2 { left:70%; } .bat.b3 { left:40%; } }
.pumpkins { font-size:1.5rem; letter-spacing:.4em; margin:6px 0 0; }
.card { border-radius:110px 110px 12px 12px; padding-top:22px; }
.rip { text-align:center; font-weight:700; letter-spacing:.3em; color:#f1e3d3; margin:0 0 4px; }
.dates { text-align:center; color:var(--dim); font-size:.8rem; margin:0 0 6px; }
.card h3 { text-align:center; }
.census { max-width:560px; margin:0 auto; padding:14px 18px; border:2px solid var(--pumpkin);
          border-radius:12px; background:rgba(247,103,7,.08); }
.census h2 { margin:0 0 8px; color:var(--pumpkin); }
.bar-row { display:grid; grid-template-columns:8.5em 1fr 3.5em; gap:10px; align-items:center; font-size:.9rem; }
.bar-row span:first-child { color:var(--dim); }
.bar-row b { text-align:right; }
.bar { height:12px; border-radius:6px; min-width:4px; }
"""

_KIND_NAME = {"file": "deleted file", "revert": "reverted commit", "contributor": "went quiet"}


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_html(altar: Altar) -> str:
    picado = "".join(
        f'<span style="background:{_PICADO_COLORS[i % len(_PICADO_COLORS)]}"></span>' for i in range(14)
    )
    ghosts = ""
    if altar.ghosts:
        items = "".join(f"<li>{e(ghost_line(g))}</li>" for g in altar.ghosts)
        ghosts = f'<h2>👻 They came back</h2>\n<ul class="ghosts">{items}</ul>'
    if altar.souls:
        souls = '<h2>🕯️ Remembered here</h2>\n<div class="grid">' + "".join(
            _card(altar, s) for s in altar.souls) + "</div>"
    else:
        souls = '<p class="empty">Nobody has died here. Yet.</p>'
    name = e(clean_text(altar.repo_name, 60))
    census = _census(altar)
    candle = '<div class="candle"><div class="flame"></div></div>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ofrenda · {name}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="picado" aria-hidden="true">{picado}</div>
<div class="sky" aria-hidden="true"><div class="moon"></div><span class="bat">🦇</span><span class="bat b2">🦇</span><span class="bat b3">🦇</span></div>
<header>
<div class="candles" aria-hidden="true">{candle * 3}</div>
<h1>OFRENDA · {name}</h1>
<p class="sub">{e(subtitle(altar))}</p>
<p class="marigolds" aria-hidden="true">{"🌼" * 12}</p>
<p class="pumpkins" aria-hidden="true">🎃💀🎃</p>
</header>
<main>
{census}
{ghosts}
{souls}
</main>
<footer>{e(footer(altar))}</footer>
</body>
</html>
"""


def _card(altar: Altar, soul: Soul) -> str:
    facts = "".join(f"<dt>{e(label)}</dt><dd>{e(value)}</dd>" for label, value in fact_rows(soul))
    verse, _ = altar.verses.get(soul.id, ("", "template"))
    verse = "\n".join(clean_text(line, 120) for line in verse.splitlines())
    cls = "card ghost" if is_ghost(soul) else "card"
    return (
        f'<article class="{cls}">'
        f'<div class="kind">{e(_KIND_NAME.get(soul.kind, soul.kind))}</div>'
        '<p class="rip">R.I.P.</p>'
        f"<h3>{e(clean_text(soul.name))}</h3>"
        f'<p class="dates">✝ {soul.born.date:%Y} – {soul.died.date:%Y}</p>'
        f"<dl>{facts}</dl>"
        f'<p class="verse">{e(verse)}</p>'
        f'<p class="label">{e(source_label(altar, soul))}</p>'
        "</article>"
    )


def _census(altar: Altar) -> str:
    if not altar.census:
        return ""
    biggest = max(altar.census.values()) or 1
    rows = "".join(
        f'<div class="bar-row"><span>{e(label)}</span>'
        f'<div class="bar" style="width:{max(2, round(100 * n / biggest))}%;'
        f'background:{_PICADO_COLORS[i % len(_PICADO_COLORS)]}"></div><b>{e(n)}</b></div>'
        for i, (label, n) in enumerate(altar.census.items())
    )
    return f'<section class="census"><h2>⚰️ Graveyard census</h2>{rows}</section>'

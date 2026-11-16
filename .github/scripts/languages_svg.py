"""Draw a language donut chart as a static SVG and point README.md at it.

Input (stdin): JSON lines, one per repository, from `gh api graphql --paginate`
with fields {name, color} for the primary language (or null).
Usage: python3 languages_svg.py <svg_path> <readme_path>
"""

import json
import math
import sys
from collections import Counter
from html import escape

SVG_PATH, README_PATH = sys.argv[1], sys.argv[2]
START, END = "<!-- LANGUAGES:START -->", "<!-- LANGUAGES:END -->"
FALLBACK_COLOR = "#8b949e"

# ---- collect counts and colors -------------------------------------------
counts: Counter[str] = Counter()
colors: dict[str, str] = {}
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    lang = json.loads(line)
    if not lang:
        continue
    counts[lang["name"]] += 1
    colors[lang["name"]] = lang.get("color") or FALLBACK_COLOR

if not counts:
    print("No public repositories with a detected language; nothing to draw.")
    sys.exit(0)

langs = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))
total = sum(counts.values())

# ---- geometry --------------------------------------------------------------
ROW_H = 26
legend_rows = len(langs)
WIDTH = 520
HEIGHT = max(280, 100 + legend_rows * ROW_H + 30)
CX, CY = 140, 84 + (HEIGHT - 84) / 2
R_OUT, R_IN = 82, 50


def point(r: float, angle: float) -> tuple[float, float]:
    # angle 0 = 12 o'clock, clockwise
    return CX + r * math.sin(angle), CY - r * math.cos(angle)


def slice_path(a0: float, a1: float) -> str:
    large = 1 if a1 - a0 > math.pi else 0
    x0, y0 = point(R_OUT, a0)
    x1, y1 = point(R_OUT, a1)
    x2, y2 = point(R_IN, a1)
    x3, y3 = point(R_IN, a0)
    return (
        f"M{x0:.2f},{y0:.2f} A{R_OUT},{R_OUT} 0 {large} 1 {x1:.2f},{y1:.2f} "
        f"L{x2:.2f},{y2:.2f} A{R_IN},{R_IN} 0 {large} 0 {x3:.2f},{y3:.2f} Z"
    )


parts = []
angle = 0.0
for name, n in langs:
    sweep = 2 * math.pi * n / total
    color = escape(colors[name])
    if sweep >= 2 * math.pi - 1e-9:  # a single language: draw a full ring
        parts.append(
            f'<circle cx="{CX}" cy="{CY:.2f}" r="{(R_OUT + R_IN) / 2}" fill="none" '
            f'stroke="{color}" stroke-width="{R_OUT - R_IN}"/>'
        )
    else:
        parts.append(f'<path d="{slice_path(angle, angle + sweep)}" fill="{color}"/>')
    angle += sweep

legend = []
LX = 270
ly0 = CY - (legend_rows * ROW_H) / 2 + ROW_H / 2
for i, (name, n) in enumerate(langs):
    y = ly0 + i * ROW_H
    pct = round(100 * n / total)
    legend.append(
        f'<circle cx="{LX}" cy="{y:.1f}" r="6" fill="{escape(colors[name])}"/>'
        f'<text x="{LX + 16}" y="{y + 5:.1f}" class="lang">{escape(name)}</text>'
        f'<text x="{WIDTH - 28}" y="{y + 5:.1f}" class="num" text-anchor="end">'
        f"{n} · {pct}%</text>"
    )

repo_word = "repository" if total == 1 else "repositories"
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT:.0f}" viewBox="0 0 {WIDTH} {HEIGHT:.0f}" role="img" aria-label="Primary languages of {total} public {repo_word}">
  <style>
    .title {{ font: 600 18px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: #e6edf3; }}
    .sub {{ font: 400 13px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: #8b949e; }}
    .lang {{ font: 500 14px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: #e6edf3; }}
    .num {{ font: 400 13px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: #8b949e; }}
    .big {{ font: 700 26px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: #e6edf3; }}
  </style>
  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1:.0f}" rx="10" fill="#0d1117" stroke="#30363d"/>
  <text x="24" y="38" class="title">Languages across my GitHub repos</text>
  <text x="24" y="60" class="sub">Primary language of my {total} public {repo_word}</text>
  {"".join(parts)}
  <text x="{CX}" y="{CY + 4:.2f}" class="big" text-anchor="middle">{total}</text>
  <text x="{CX}" y="{CY + 22:.2f}" class="sub" text-anchor="middle">repos</text>
  {"".join(legend)}
</svg>
"""

with open(SVG_PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(svg)

# ---- point README at the SVG (once; later runs only change the SVG) --------
svg_name = SVG_PATH.replace("\\", "/").split("/")[-1]
block = (
    '<p align="center">\n'
    f'  <img src="./{svg_name}" alt="Primary languages across my GitHub repositories" width="520"/>\n'
    "</p>"
)

text = open(README_PATH, encoding="utf-8", newline="").read()
if START not in text or END not in text:
    sys.exit(f"README is missing the {START} / {END} markers")

nl = "\r\n" if "\r\n" in text else "\n"
before = text[: text.index(START) + len(START)]
after = text[text.index(END):]
new_text = f"{before}{nl}{block.replace(chr(10), nl)}{nl}{after}"

if new_text != text:
    with open(README_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)
    print("README updated.")
print(f"Drew {svg_name}: " + ", ".join(f"{k} {v}" for k, v in langs))

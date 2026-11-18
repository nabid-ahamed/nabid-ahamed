"""Draw the language pie chart as a static SVG and point README.md at it.

The look copies the Mermaid `pie showData` chart this README used to have (same dark
palette, percentages inside the slices, "Name [count]" legend), but as a plain image,
so GitHub adds no pan/zoom buttons to it.

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

# Mermaid's dark-theme pie colours, in order; they repeat after the 12th slice.
PALETTE = [
    "#0b0000", "#4d1037", "#3f5258", "#4f2f1b", "#6e0a0a", "#3b0048",
    "#995a01", "#154706", "#161722", "#00296f", "#01629c", "#cccccc",
]
FONT = "'trebuchet ms', verdana, arial, sans-serif"

# ---- collect counts --------------------------------------------------------
counts: Counter[str] = Counter()
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    lang = json.loads(line)
    if lang:
        counts[lang["name"]] += 1

if not counts:
    print("No public repositories with a detected language; nothing to draw.")
    sys.exit(0)

langs = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))
total = sum(counts.values())

# ---- geometry --------------------------------------------------------------
WIDTH = 760
R = 190                      # pie radius
CX = 40 + R                  # pie centre x
TOP = 112                    # top of the pie
ROW_H = 24                   # legend row height
legend_h = len(langs) * ROW_H
HEIGHT = TOP + max(2 * R, legend_h) + 24
CY = TOP + max(2 * R, legend_h) / 2
LX = CX + R + 50             # legend x


def point(r: float, angle: float) -> tuple[float, float]:
    # angle 0 = 12 o'clock, clockwise (same as Mermaid)
    return CX + r * math.sin(angle), CY - r * math.cos(angle)


slices, labels = [], []
angle = 0.0
for i, (name, n) in enumerate(langs):
    color = PALETTE[i % len(PALETTE)]
    sweep = 2 * math.pi * n / total
    if sweep >= 2 * math.pi - 1e-9:  # one language: a full circle
        slices.append(f'<circle cx="{CX}" cy="{CY:.2f}" r="{R}" fill="{color}" class="slice"/>')
    else:
        x0, y0 = point(R, angle)
        x1, y1 = point(R, angle + sweep)
        large = 1 if sweep > math.pi else 0
        slices.append(
            f'<path d="M{CX},{CY:.2f} L{x0:.2f},{y0:.2f} A{R},{R} 0 {large} 1 {x1:.2f},{y1:.2f} Z" '
            f'fill="{color}" class="slice"/>'
        )
    lx, ly = point(R * 0.75, angle + sweep / 2)
    labels.append(
        f'<text x="{lx:.2f}" y="{ly:.2f}" class="pct" text-anchor="middle" '
        f'dominant-baseline="central">{round(100 * n / total)}%</text>'
    )
    angle += sweep

legend = []
ly0 = CY - legend_h / 2
for i, (name, n) in enumerate(langs):
    y = ly0 + i * ROW_H
    legend.append(
        f'<rect x="{LX}" y="{y + 3:.1f}" width="18" height="18" fill="{PALETTE[i % len(PALETTE)]}" '
        f'stroke="#30363d" stroke-width="1"/>'
        f'<text x="{LX + 26}" y="{y + 17:.1f}" class="legend">{escape(name)} [{n}]</text>'
    )

repo_word = "repository" if total == 1 else "repositories"
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT:.0f}" viewBox="0 0 {WIDTH} {HEIGHT:.0f}" role="img" aria-label="Primary languages of {total} public {repo_word}">
  <style>
    .sub {{ font: italic 400 17px {FONT}; fill: #e6edf3; }}
    .title {{ font: 400 25px {FONT}; fill: #cccccc; }}
    .pct {{ font: 400 17px {FONT}; fill: #cccccc; }}
    .legend {{ font: 400 17px {FONT}; fill: #cccccc; }}
    .slice {{ stroke: #000000; stroke-width: 2px; }}
  </style>
  <rect width="{WIDTH}" height="{HEIGHT:.0f}" rx="6" fill="#0d1117"/>
  <text x="{WIDTH / 2}" y="30" class="sub" text-anchor="middle">Primary language of my {total} public {repo_word}</text>
  <text x="{CX}" y="{TOP - 26}" class="title" text-anchor="middle">Languages across my GitHub repos</text>
  {"".join(slices)}
  <circle cx="{CX}" cy="{CY:.2f}" r="{R}" fill="none" stroke="#000000" stroke-width="2"/>
  {"".join(labels)}
  {"".join(legend)}
</svg>
"""

with open(SVG_PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(svg)

# ---- point README at the SVG (once; later runs only change the SVG) --------
svg_name = SVG_PATH.replace("\\", "/").split("/")[-1]
block = (
    '<p align="center">\n'
    f'  <img src="./{svg_name}" alt="Primary languages across my GitHub repositories" width="100%"/>\n'
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

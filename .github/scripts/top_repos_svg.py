"""Draw a "Top contributed repos" card as a static SVG.

Sums the user's commits, pull requests, issues and reviews per repository
across every year since the account was created, using `gh api graphql`.
Usage: python3 top_repos_svg.py <owner> <svg_path> [limit]
Needs: gh (authenticated via GH_TOKEN).
"""

import base64
import json
import subprocess
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from html import escape

OWNER, SVG_PATH = sys.argv[1], sys.argv[2]
LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else 5
PROFILE_REPO = f"{OWNER}/{OWNER}".lower()  # README edits, not project work


def gql(query: str, **variables: str) -> dict:
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        args += ["-F", f"{key}={value}"]
    out = subprocess.run(args, check=True, capture_output=True, text=True, encoding="utf-8").stdout
    return json.loads(out)["data"]


created = gql("query($login:String!){user(login:$login){createdAt}}", login=OWNER)["user"]["createdAt"]
start_year = int(created[:4])
now = datetime.now(timezone.utc)

REPO_FIELDS = "repository { nameWithOwner stargazerCount owner { login avatarUrl(size: 64) } }"
YEAR_QUERY = f"""
query($login: String!, $from: DateTime!, $to: DateTime!) {{
  user(login: $login) {{
    contributionsCollection(from: $from, to: $to) {{
      commitContributionsByRepository(maxRepositories: 100) {{ {REPO_FIELDS} contributions {{ totalCount }} }}
      pullRequestContributionsByRepository(maxRepositories: 100) {{ {REPO_FIELDS} contributions {{ totalCount }} }}
      issueContributionsByRepository(maxRepositories: 100) {{ {REPO_FIELDS} contributions {{ totalCount }} }}
      pullRequestReviewContributionsByRepository(maxRepositories: 100) {{ {REPO_FIELDS} contributions {{ totalCount }} }}
    }}
  }}
}}"""

totals: dict[str, int] = defaultdict(int)
info: dict[str, dict] = {}
for year in range(start_year, now.year + 1):
    window_from = max(f"{year}-01-01T00:00:00Z", created)
    window_to = min(f"{year}-12-31T23:59:59Z", now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    coll = gql(YEAR_QUERY, login=OWNER, **{"from": window_from, "to": window_to})["user"]["contributionsCollection"]
    for kind in coll.values():
        for entry in kind:
            repo = entry["repository"]
            key = repo["nameWithOwner"]
            if key.lower() == PROFILE_REPO:
                continue
            totals[key] += entry["contributions"]["totalCount"]
            info[key] = repo

top = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0].lower()))[:LIMIT]
if not top:
    print("No public contributions found; nothing to draw.")
    sys.exit(0)


def avatar_data_uri(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = resp.read()
            mime = resp.headers.get_content_type() or "image/png"
        return f"data:{mime};base64,{base64.b64encode(data).decode()}"
    except Exception as exc:  # avatar is decoration; never fail the card for it
        print(f"warning: could not fetch avatar {url}: {exc}")
        return ""


avatars: dict[str, str] = {}
for key, _ in top:
    owner = info[key]["owner"]
    if owner["login"] not in avatars:
        avatars[owner["login"]] = avatar_data_uri(owner["avatarUrl"])

# ---- draw -------------------------------------------------------------------
WIDTH, ROW_H, TOP = 520, 46, 84
HEIGHT = TOP + len(top) * ROW_H + 18
best = top[0][1]
BAR_X, BAR_W = 300, 130

rows = []
for i, (key, count) in enumerate(top):
    repo = info[key]
    owner = repo["owner"]["login"]
    name = key.split("/", 1)[1]
    y = TOP + i * ROW_H  # top of the row
    cy = y + ROW_H / 2
    av = avatars.get(owner, "")
    avatar = (
        f'<clipPath id="av{i}"><circle cx="66" cy="{cy:.1f}" r="14"/></clipPath>'
        f'<image href="{av}" x="52" y="{cy - 14:.1f}" width="28" height="28" clip-path="url(#av{i})"/>'
        if av
        else f'<circle cx="66" cy="{cy:.1f}" r="14" fill="#30363d"/>'
    )
    owner_label = "" if owner.lower() == OWNER.lower() else f'<tspan class="owner">{escape(owner)}/</tspan>'
    bar = max(4, BAR_W * count / best)
    rows.append(
        f'<text x="24" y="{cy + 5:.1f}" class="rank">{i + 1}</text>'
        f"{avatar}"
        f'<text x="92" y="{cy - 2:.1f}" class="repo">{owner_label}{escape(name)}</text>'
        f'<text x="92" y="{cy + 15:.1f}" class="meta">★ {repo["stargazerCount"]}</text>'
        f'<rect x="{BAR_X}" y="{cy - 4:.1f}" width="{BAR_W}" height="8" rx="4" fill="#21262d"/>'
        f'<rect x="{BAR_X}" y="{cy - 4:.1f}" width="{bar:.1f}" height="8" rx="4" fill="#3fb950"/>'
        f'<text x="{WIDTH - 24}" y="{cy + 5:.1f}" class="count" text-anchor="end">{count}</text>'
    )
    if i < len(top) - 1:
        rows.append(f'<line x1="24" x2="{WIDTH - 24}" y1="{y + ROW_H:.1f}" y2="{y + ROW_H:.1f}" stroke="#21262d"/>')

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="Top {len(top)} repositories by contributions">
  <style>
    .title {{ font: 600 18px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: #e6edf3; }}
    .sub {{ font: 400 13px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: #8b949e; }}
    .rank {{ font: 700 15px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: #8b949e; }}
    .repo {{ font: 600 14px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: #e6edf3; }}
    .owner {{ font-weight: 400; fill: #8b949e; }}
    .meta {{ font: 400 12px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: #8b949e; }}
    .count {{ font: 600 14px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: #e6edf3; }}
  </style>
  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="10" fill="#0d1117" stroke="#30363d"/>
  <text x="24" y="38" class="title">Top contributed repositories</text>
  <text x="24" y="60" class="sub">Commits, pull requests &amp; issues since {start_year}</text>
  {"".join(rows)}
</svg>
"""

with open(SVG_PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(svg)
print("Drew top repos: " + ", ".join(f"{k} {v}" for k, v in top))

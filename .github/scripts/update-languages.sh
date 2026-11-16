#!/usr/bin/env bash
# Rebuilds the language pie chart between the LANGUAGES markers in README.md.
# Counts the primary language of each public, non-fork repo owned by $OWNER.
# Needs: gh (authenticated via GH_TOKEN), python3.
set -euo pipefail

OWNER="${OWNER:?set OWNER to the GitHub username}"
README="${README:-README.md}"

counts=$(gh api --paginate "users/${OWNER}/repos?per_page=100&type=owner" \
  --jq '.[] | select(.fork == false and .language != null) | .language' |
  sort | uniq -c | sort -k1,1nr -k2)

if [ -z "$counts" ]; then
  echo "No public repositories with a detected language; leaving README unchanged."
  exit 0
fi

total=$(awk '{ s += $1 } END { print s }' <<<"$counts")

chart_file=$(mktemp)
{
  echo "<p align=\"center\"><i>Primary language of my ${total} public repositories</i></p>"
  echo
  echo '```mermaid'
  echo 'pie showData title Languages across my GitHub repos'
  while read -r n lang; do
    printf '    "%s" : %s\n' "${lang//\"/}" "$n"
  done <<<"$counts"
  echo '```'
} >"$chart_file"

python3 - "$README" "$chart_file" <<'PY'
import sys

readme_path, chart_path = sys.argv[1], sys.argv[2]
start, end = "<!-- LANGUAGES:START -->", "<!-- LANGUAGES:END -->"

text = open(readme_path, encoding="utf-8", newline="").read()
chart = open(chart_path, encoding="utf-8").read().rstrip("\n")

if start not in text or end not in text:
    sys.exit(f"README is missing the {start} / {end} markers")

# Keep the README's existing line endings (CRLF or LF).
nl = "\r\n" if "\r\n" in text else "\n"
chart = chart.replace("\n", nl)

before = text[: text.index(start) + len(start)]
after = text[text.index(end):]
new_text = f"{before}{nl}{chart}{nl}{after}"

if new_text != text:
    open(readme_path, "w", encoding="utf-8", newline="").write(new_text)
    print("README chart updated.")
else:
    print("README chart already up to date.")
PY

rm -f "$chart_file"

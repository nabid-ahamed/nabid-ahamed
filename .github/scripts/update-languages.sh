#!/usr/bin/env bash
# Redraws languages.svg (a pie chart of primary languages) and makes sure
# README.md shows it between the LANGUAGES markers.
# Counts the primary language of each public, non-fork repo owned by $OWNER.
# Needs: gh (authenticated via GH_TOKEN), python3.
set -euo pipefail

OWNER="${OWNER:?set OWNER to the GitHub username}"
README="${README:-README.md}"
SVG="${SVG:-languages.svg}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# One JSON line per repo: {"name": "...", "color": "#..."} or null.
gh api graphql --paginate -F owner="$OWNER" -f query='
  query($owner: String!, $endCursor: String) {
    user(login: $owner) {
      repositories(first: 100, after: $endCursor, ownerAffiliations: OWNER,
                   privacy: PUBLIC, isFork: false) {
        nodes { primaryLanguage { name color } }
        pageInfo { hasNextPage endCursor }
      }
    }
  }' --jq '.data.user.repositories.nodes[] | .primaryLanguage' |
  python3 "$here/languages_svg.py" "$SVG" "$README"

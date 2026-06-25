#!/usr/bin/env bash
# Publish wiki/*.md to the GitHub Wiki.
# Prereq (one time): create the first wiki page in the browser so the wiki git
# repo exists — see wiki/README.md.
set -euo pipefail

REPO="israelortizcpsc/Gauge-CAPEX-Benchmarking-Dashboard"
SRC="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"

# Use the gh token for auth without baking it into a stored remote.
TOKEN="$(gh auth token)"
WIKI_URL="https://x-access-token:${TOKEN}@github.com/${REPO}.wiki.git"

git clone "$WIKI_URL" "$TMP"
cp "$SRC"/Home.md "$SRC"/How-This-Was-Built.md "$SRC"/Architecture-and-Decisions.md "$TMP"/

cd "$TMP"
git add -A
if git diff --cached --quiet; then
  echo "Wiki already up to date."
else
  git -c user.name="Israel Ortiz" -c user.email="israeljortizcpsc@gmail.com" \
    commit -m "Sync wiki from repo"
  git push origin HEAD
  echo "Wiki published."
fi

rm -rf "$TMP"

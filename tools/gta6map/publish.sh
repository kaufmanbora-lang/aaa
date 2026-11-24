#!/usr/bin/env bash
# Publish the committed docs/ folder of the current branch to the gh-pages branch (the site GitHub Pages serves).
# Run after committing; does nothing if gh-pages already holds the same files.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git fetch -q origin gh-pages 2>/dev/null || true
TREE=$(git rev-parse HEAD:docs)
PARENT=$(git rev-parse -q --verify origin/gh-pages || true)
if [ -n "$PARENT" ] && [ "$(git rev-parse "$PARENT^{tree}")" = "$TREE" ]; then echo "gh-pages is already up to date"; exit 0; fi
MSG="Publish map site (docs/ @ $(git rev-parse --short HEAD))"
if [ -n "$PARENT" ]; then SHA=$(git commit-tree "$TREE" -p "$PARENT" -m "$MSG"); else SHA=$(git commit-tree "$TREE" -m "$MSG"); fi
git push origin "$SHA:refs/heads/gh-pages"
echo "published $SHA"

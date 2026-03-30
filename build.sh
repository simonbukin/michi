#!/usr/bin/env bash
set -euo pipefail

# Build both mdbooks into dist/ for deployment.
# Usage: ./build.sh

ROOT="$(cd "$(dirname "$0")" && pwd)"
DIST="$ROOT/dist"
rm -rf "$DIST"
mkdir -p "$DIST"

echo "==> Generating main book summary + symlinks..."
python3 "$ROOT/textbook/gen_summary.py"

echo "==> Building main textbook..."
mdbook build "$ROOT/textbook" --dest-dir "$DIST/textbook"

echo "==> Generating immersion guide summary + symlinks..."
python3 "$ROOT/immersion/gen_summary.py"

echo "==> Building immersion guide..."
mdbook build "$ROOT/immersion" --dest-dir "$DIST/immersion"

echo "==> Generating colloquial patterns summary + symlinks..."
python3 "$ROOT/colloquial/gen_summary.py"

echo "==> Building colloquial patterns guide..."
mdbook build "$ROOT/colloquial" --dest-dir "$DIST/colloquial"

echo "==> Creating landing page..."
cp "$ROOT/public/index.html" "$DIST/index.html"

echo "==> Done. Output in $DIST/"

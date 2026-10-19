#!/usr/bin/env bash
# Points this clone at the tracked hooks. Hooks live in the clone's config, so run it once per clone.
cd "$(git rev-parse --show-toplevel)" || exit 1
chmod +x scripts/hooks/pre-commit
git config core.hooksPath scripts/hooks
echo "core.hooksPath = scripts/hooks"

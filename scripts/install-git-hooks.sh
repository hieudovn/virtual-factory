#!/bin/bash
# install-git-hooks.sh — Install git hooks into the local .git/hooks directory
set -euo pipefail

HOOKS_DIR="$(cd "$(dirname "$0")/git-hooks" && pwd)"
GIT_HOOKS_DIR="$(git rev-parse --git-dir)/hooks"

echo "Installing git hooks from $HOOKS_DIR to $GIT_HOOKS_DIR"

for hook in "$HOOKS_DIR"/*; do
    hook_name=$(basename "$hook")
    # Skip non-executable files and this installer
    if [[ "$hook_name" == "install-git-hooks.sh" ]]; then
        continue
    fi
    cp "$hook" "$GIT_HOOKS_DIR/$hook_name"
    chmod +x "$GIT_HOOKS_DIR/$hook_name"
    echo "  Installed: $hook_name"
done

echo "Git hooks installed successfully."

#!/bin/sh
set -eu

repo_root=$(git rev-parse --show-toplevel)

if ! command -v ggshield >/dev/null 2>&1; then
    printf 'ggshield is required by the repository Git hooks.\n' >&2
    printf 'Install it, run "ggshield auth login", then rerun this script.\n' >&2
    exit 1
fi

if ! ggshield api-status --no-check-for-updates >/dev/null 2>&1; then
    printf 'ggshield is not authenticated or cannot reach GitGuardian.\n' >&2
    printf 'Run "ggshield auth login", then rerun this script.\n' >&2
    exit 1
fi

for hook in pre-commit pre-push; do
    if [ ! -x "$repo_root/.githooks/$hook" ]; then
        printf 'Missing or non-executable hook: %s/.githooks/%s\n' "$repo_root" "$hook" >&2
        exit 1
    fi
done
git -C "$repo_root" config --local core.hooksPath .githooks
printf 'Git hooks enabled: %s/.githooks\n' "$repo_root"

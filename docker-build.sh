#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
git_tag="$(git describe --tags --exact-match HEAD 2>/dev/null || true)"
LABSMANAGER_GIT_TAG="$git_tag" docker compose build lab-server "$@"

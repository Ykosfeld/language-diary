#!/usr/bin/env bash
set -e
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/src/main.py" "$@"

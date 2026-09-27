#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export IDF_PATH="${IDF_PATH:-/Users/jimcochran-miller/esp-idf-v5.5.5}"
source "$IDF_PATH/export.sh" >/dev/null
export PATH="$IDF_PYTHON_ENV_PATH/bin:$ROOT/.venv/bin:$PATH"
exec "$IDF_PYTHON_ENV_PATH/bin/python" "$IDF_PATH/tools/idf.py" -C "$ROOT/firmware" "$@"

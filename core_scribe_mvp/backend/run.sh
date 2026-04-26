#!/usr/bin/env bash
# Convenience launcher. Run `bash run.sh` from inside core_scribe_mvp/backend.
set -euo pipefail

cd "$(dirname "$0")"

# macOS / conda envs frequently load multiple OpenMP runtimes (torch +
# ctranslate2 + numpy via different wheels). Allow them to coexist instead
# of crashing on import. Harmless in this single-process server context.
export KMP_DUPLICATE_LIB_OK="${KMP_DUPLICATE_LIB_OK:-TRUE}"

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

echo "▶ Medics4ALL Core Scribe — http://${HOST}:${PORT}"
exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload

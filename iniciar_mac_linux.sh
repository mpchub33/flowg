#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export FOLLOW_SUBJECT_HOST=127.0.0.1
export FOLLOW_SUBJECT_OPEN_BROWSER=1
export PORT=8501
PYTHON=""
for candidate in python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then PYTHON="$candidate"; break; fi
done
if [[ -z "$PYTHON" ]]; then echo "Instala Python 3.10 o 3.11 y vuelve a ejecutar este archivo."; exit 1; fi
if [[ ! -x .venv/bin/python ]]; then "$PYTHON" -m venv .venv; fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python comprobar_gpu.py
.venv/bin/python app.py

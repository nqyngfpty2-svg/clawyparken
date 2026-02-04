#!/usr/bin/env bash
set -euo pipefail

# Minimal installer for a VPS.
# Installs deps into .venv and runs migrations.

cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

./.venv/bin/pip install -U pip wheel
./.venv/bin/pip install -r requirements.txt

./.venv/bin/python -c "from parking_app.app.db import migrate; migrate(); print('migrate ok')"

echo "OK"

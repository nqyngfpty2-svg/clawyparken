#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./.venv/bin/uvicorn parking_app.app.main:app --host 127.0.0.1 --port 18880 --reload

.PHONY: help venv install dev lint fmt test migrate run

PY?=.venv/bin/python
PIP?=.venv/bin/pip
UVICORN?=.venv/bin/uvicorn

help:
	@echo "Targets:"
	@echo "  venv      - create venv"
	@echo "  install   - install deps"
	@echo "  dev       - run dev server (127.0.0.1:18880)"
	@echo "  migrate   - run sqlite migrations (safe to re-run)"

venv:
	python3 -m venv .venv
	@echo "Now run: . .venv/bin/activate"

install:
	$(PIP) install -U pip wheel
	$(PIP) install -r requirements.txt

migrate:
	$(PY) -c "from parking_app.app.db import migrate; migrate(); print('ok')"

# Dev server
# Use: make dev
# then open http://127.0.0.1:18880
#
# Note: in production we run behind nginx via systemd.

dev:
	$(UVICORN) parking_app.app.main:app --host 127.0.0.1 --port 18880 --reload

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from datetime import datetime


def ensure_admin_code(secrets_dir: Path) -> str:
    secrets_dir.mkdir(parents=True, exist_ok=True)
    p = secrets_dir / "admin_code.txt"
    if p.exists():
        return p.read_text(encoding="utf-8", errors="replace").strip()
    code = secrets.token_urlsafe(18)
    p.write_text(code + "\n", encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except Exception:
        pass
    return code


def announce_path(data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "announcement.json"


def load_announcement(data_dir: Path) -> dict | None:
    p = announce_path(data_dir)
    if not p.exists():
        return None
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            return None
        if not obj.get("enabled"):
            return None
        return obj
    except Exception:
        return None


def save_announcement(data_dir: Path, title: str, body: str, level: str, enabled: bool) -> None:
    p = announce_path(data_dir)
    obj = {
        "enabled": bool(enabled),
        "level": (level or "info"),
        "title": (title or "").strip(),
        "body": (body or "").strip(),
        "updated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

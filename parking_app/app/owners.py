from __future__ import annotations

import json
import secrets
from pathlib import Path

SECRETS_DIR = Path(__file__).resolve().parents[1] / "secrets"
OWNERS_PATH = SECRETS_DIR / "owners.json"


def generate_owner_codes(n: int = 60) -> dict[str, str]:
    # 4 hex chars => 65536 space; ensure uniqueness.
    codes: set[str] = set()
    out: dict[str, str] = {}
    for i in range(1, n + 1):
        spot = f"P{i:02d}"
        code = None
        while code is None or code in codes:
            code = secrets.token_hex(2).upper()  # 4 hex chars
        codes.add(code)
        out[spot] = code
    return out


def ensure_owner_codes() -> dict[str, str]:
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    if OWNERS_PATH.exists():
        return json.loads(OWNERS_PATH.read_text(encoding="utf-8"))
    mapping = generate_owner_codes(60)
    OWNERS_PATH.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        OWNERS_PATH.chmod(0o600)
    except Exception:
        pass
    return mapping

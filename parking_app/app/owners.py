from __future__ import annotations

import json
import secrets
from pathlib import Path

SECRETS_DIR = Path(__file__).resolve().parents[1] / "secrets"
OWNERS_PATH = SECRETS_DIR / "owners.json"


def _new_code(used: set[str]) -> str:
    code = None
    while code is None or code in used:
        code = secrets.token_hex(2).upper()  # 4 hex chars
    used.add(code)
    return code


def generate_owner_codes(n: int = 60) -> dict[str, str]:
    """Generate owner codes for both parking lots.

    Spot keys:
      - Bankparkplatz: P01..P60
      - Postparkplatz: PP01..PP60
    """
    out: dict[str, str] = {}
    used: set[str] = set()

    for i in range(1, n + 1):
        out[f"P{i:02d}"] = _new_code(used)

    for i in range(1, n + 1):
        out[f"PP{i:02d}"] = _new_code(used)

    return out


def ensure_owner_codes() -> dict[str, str]:
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)

    if OWNERS_PATH.exists():
        mapping = json.loads(OWNERS_PATH.read_text(encoding="utf-8"))

        # Backward compatibility: old installs had only P01..P60.
        # Keep existing codes and append missing Postparkplatz spots.
        used = set(mapping.values())
        changed = False
        for i in range(1, 61):
            key = f"PP{i:02d}"
            if key not in mapping:
                mapping[key] = _new_code(used)
                changed = True

        if changed:
            OWNERS_PATH.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            try:
                OWNERS_PATH.chmod(0o600)
            except Exception:
                pass

        return mapping

    mapping = generate_owner_codes(60)
    OWNERS_PATH.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        OWNERS_PATH.chmod(0o600)
    except Exception:
        pass
    return mapping

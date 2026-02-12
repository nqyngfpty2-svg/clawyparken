from __future__ import annotations

import json
import secrets
from pathlib import Path

SECRETS_DIR = Path(__file__).resolve().parents[1] / "secrets"
OWNERS_PATH = SECRETS_DIR / "owners.json"

BANK_SPOTS = [f"P{i:02d}" for i in range(1, 61)]

# Internal spot ids for Postparkplatz (prefix keeps names unique vs Bankparkplatz).
# Visible labels are the suffix after "PP::".
POST_SPOTS = [
    "PP::P72",
    "PP::P12",
    "PP::P17-13",
    "PP::P18-15",
    "PP::P19-1",
    "PP::P20-2",
    "PP::P21-3",
    "PP::P22-4",
    "PP::P23-5",
    "PP::P24-6",
    "PP::P25-7",
    "PP::P26-8",
    "PP::P27-9",
    "PP::P29-11",
    "PP::P27",
    "PP::P28",
    "PP::P29",
    "PP::P30",
    "PP::P31",
    "PP::P32",
    "PP::P33",
    "PP::P34",
    "PP::P35",
]


def visible_spot_label(name: str) -> str:
    if name.startswith("PP::"):
        return name[4:]
    return name


def is_post_spot(name: str) -> bool:
    return name.startswith("PP::") or name.startswith("PP")


def _new_code(used: set[str]) -> str:
    code = None
    while code is None or code in used:
        code = secrets.token_hex(2).upper()  # 4 hex chars
    used.add(code)
    return code


def generate_owner_codes() -> dict[str, str]:
    """Generate owner codes for both parking lots.

    Spot keys:
      - Bankparkplatz: P01..P60
      - Postparkplatz: PP::Pxx / PP::Pxx-y (internal ids)
    """
    out: dict[str, str] = {}
    used: set[str] = set()

    for spot in BANK_SPOTS:
        out[spot] = _new_code(used)

    for spot in POST_SPOTS:
        out[spot] = _new_code(used)

    return out


def ensure_owner_codes() -> dict[str, str]:
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)

    if OWNERS_PATH.exists():
        mapping = json.loads(OWNERS_PATH.read_text(encoding="utf-8"))

        # Backward compatibility: keep existing keys, append any missing new keys.
        used = set(mapping.values())
        changed = False

        for key in BANK_SPOTS + POST_SPOTS:
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

    mapping = generate_owner_codes()
    OWNERS_PATH.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        OWNERS_PATH.chmod(0o600)
    except Exception:
        pass
    return mapping

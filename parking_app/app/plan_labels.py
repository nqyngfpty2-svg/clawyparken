from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parents[1]
PLAN_DIR = BASE_DIR / "plan"
DATA_DIR = BASE_DIR / "data"
SECRETS_DIR = BASE_DIR / "secrets"

PLAN_IMAGE = PLAN_DIR / "plan-1.png"
LABELS_PATH = DATA_DIR / "plan_labels.json"
ADMIN_TOKEN_PATH = SECRETS_DIR / "plan_admin_token.txt"


def ensure_admin_token() -> str:
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    if ADMIN_TOKEN_PATH.exists():
        return ADMIN_TOKEN_PATH.read_text(encoding="utf-8").strip()
    token = secrets.token_urlsafe(24)
    ADMIN_TOKEN_PATH.write_text(token + "\n", encoding="utf-8")
    try:
        ADMIN_TOKEN_PATH.chmod(0o600)
    except Exception:
        pass
    return token


def load_labels() -> list[dict[str, Any]]:
    if not LABELS_PATH.exists():
        return []
    return json.loads(LABELS_PATH.read_text(encoding="utf-8"))


def save_labels(labels: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_PATH.write_text(json.dumps(labels, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def render_annotated(out_path: Path) -> None:
    labels = load_labels()
    img = Image.open(PLAN_IMAGE).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Use a default font; PIL will fall back.
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 26)
    except Exception:
        font = ImageFont.load_default()

    for lab in labels:
        n = str(lab.get("n"))
        x = int(lab.get("x"))
        y = int(lab.get("y"))
        r = 18
        # circle
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 220), outline=(0, 0, 0, 255), width=2)
        # number centered
        bbox = draw.textbbox((0, 0), n, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((x - tw / 2, y - th / 2 - 1), n, fill=(0, 0, 0, 255), font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out_path, format="PNG")

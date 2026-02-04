from __future__ import annotations

import subprocess
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")


def send_email(to: str, subject: str, body: str) -> None:
    tmp = Path("/tmp/parking_mail.txt")
    tmp.write_text(body, encoding="utf-8")
    cmd = [
        "python3",
        str(WORKSPACE / "email" / "strato_send.py"),
        "--to",
        to,
        "--subject",
        subject,
        "--body-file",
        str(tmp),
    ]
    subprocess.run(cmd, cwd=str(WORKSPACE), check=False)

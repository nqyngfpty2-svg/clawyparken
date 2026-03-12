from __future__ import annotations

import os
import shutil
import subprocess
from email.message import EmailMessage
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")


def _send_via_strato(to: str, subject: str, body: str) -> bool:
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
    res = subprocess.run(cmd, cwd=str(WORKSPACE), check=False)
    return res.returncode == 0


def _send_via_sendmail(to: str, subject: str, body: str) -> bool:
    sendmail = shutil.which("sendmail")
    if not sendmail:
        return False

    from_addr = os.getenv("PARKING_MAIL_FROM", "noreply@localhost")
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    res = subprocess.run(
        [sendmail, "-t", "-i"],
        input=msg.as_string(),
        text=True,
        check=False,
    )
    return res.returncode == 0


def send_email(to: str, subject: str, body: str) -> None:
    # Toby-Präferenz: STRATO-first.
    if _send_via_strato(to, subject, body):
        return

    # Plesk-Setups können SMTP blockieren und nur Sendmail erlauben.
    if _send_via_sendmail(to, subject, body):
        return

    raise RuntimeError("E-Mail-Versand fehlgeschlagen (weder STRATO noch Sendmail erfolgreich).")

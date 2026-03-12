from __future__ import annotations

import os
import shutil
import subprocess
from email.message import EmailMessage


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
    # Projektregel clawyparken: kein STRATO, nur lokales Sendmail (Plesk-kompatibel).
    if _send_via_sendmail(to, subject, body):
        return

    raise RuntimeError("E-Mail-Versand fehlgeschlagen (Sendmail nicht verfügbar oder Fehler beim Versand).")

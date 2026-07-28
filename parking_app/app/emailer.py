from __future__ import annotations

import os
import shutil
import subprocess
from email.message import EmailMessage


def _build_msg(to: str, subject: str, body: str, from_addr: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def _send_via_sendmail(msg: EmailMessage) -> bool:
    sendmail = shutil.which("sendmail")
    if not sendmail:
        for candidate in ("/usr/sbin/sendmail", "/usr/lib/sendmail"):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                sendmail = candidate
                break
    if not sendmail:
        return False

    res = subprocess.run(
        [sendmail, "-t", "-i"],
        input=msg.as_string(),
        text=True,
        check=False,
    )
    return res.returncode == 0


def send_email(to: str, subject: str, body: str) -> None:
    from_addr = os.getenv("PARKING_MAIL_FROM") or "noreply@localhost"
    msg = _build_msg(to=to, subject=subject, body=body, from_addr=from_addr)

    if _send_via_sendmail(msg):
        return

    raise RuntimeError("E-Mail-Versand über lokales sendmail fehlgeschlagen.")

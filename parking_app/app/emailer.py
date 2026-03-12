from __future__ import annotations

import os
import shutil
import smtplib
import subprocess
from email.message import EmailMessage
from pathlib import Path


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y", "ja"}


def _read_send_email_cfg() -> dict[str, str]:
    """Liest optional parking_app/secrets/send_email.txt (key=value oder key: value)."""
    cfg_path = Path(__file__).resolve().parents[1] / "secrets" / "send_email.txt"
    if not cfg_path.exists():
        return {}

    alias = {
        "host": "host",
        "hostname": "host",
        "server": "host",
        "smtp_host": "host",
        "port": "port",
        "smtp_port": "port",
        "user": "user",
        "username": "user",
        "smtp_user": "user",
        "pass": "password",
        "password": "password",
        "smtp_password": "password",
        "from": "from",
        "from_addr": "from",
        "mail_from": "from",
        "starttls": "starttls",
        "tls": "starttls",
        "smtp_starttls": "starttls",
        "ssl": "ssl",
        "smtp_ssl": "ssl",
    }

    data: dict[str, str] = {}
    raw = cfg_path.read_text(encoding="utf-8", errors="ignore")
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue

        if "=" in line:
            key, value = line.split("=", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            continue

        key = key.strip().lower()
        value = value.strip().strip('"').strip("'")
        mapped = alias.get(key)
        if mapped:
            data[mapped] = value

    return data


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
        return False

    res = subprocess.run(
        [sendmail, "-t", "-i"],
        input=msg.as_string(),
        text=True,
        check=False,
    )
    return res.returncode == 0


def _send_via_smtp(msg: EmailMessage, cfg: dict[str, str]) -> bool:
    host = (cfg.get("host") or "").strip()
    if not host:
        return False

    try:
        port = int((cfg.get("port") or "587").strip())
    except ValueError:
        port = 587

    user = (cfg.get("user") or "").strip()
    password = cfg.get("password") or ""
    use_ssl = _parse_bool(cfg.get("ssl"), default=False)
    use_starttls = _parse_bool(cfg.get("starttls"), default=(not use_ssl and port == 587))

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host=host, port=port, timeout=20) as smtp:
                smtp.ehlo()
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host=host, port=port, timeout=20) as smtp:
                smtp.ehlo()
                if use_starttls:
                    smtp.starttls()
                    smtp.ehlo()
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
        return True
    except Exception:
        return False


def send_email(to: str, subject: str, body: str) -> None:
    cfg = _read_send_email_cfg()
    from_addr = os.getenv("PARKING_MAIL_FROM") or cfg.get("from") or "noreply@localhost"
    msg = _build_msg(to=to, subject=subject, body=body, from_addr=from_addr)

    # Wenn send_email.txt vorhanden ist, zuerst SMTP versuchen (z. B. STRATO-Postfach).
    if _send_via_smtp(msg, cfg):
        return

    # Fallback für Plesk/local MTA.
    if _send_via_sendmail(msg):
        return

    raise RuntimeError("E-Mail-Versand fehlgeschlagen (weder SMTP aus secrets/send_email.txt noch lokales sendmail erfolgreich).")

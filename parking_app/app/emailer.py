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


def _read_send_email_txt() -> dict[str, str]:
    """
    Liest optionale SMTP-Konfiguration aus parking_app/secrets/send_email.txt.

    Unterstützte Formate pro Zeile:
    - key=value
    - key: value
    - Kommentare mit # oder ;

    Bekannte Schlüssel (Alias-Mapping):
    host/hostname/server/smtp_host
    port/smtp_port
    user/username/smtp_user
    pass/password/smtp_password
    from/from_addr/mail_from/smtp_from
    tls/starttls/smtp_starttls
    ssl/smtp_ssl
    """
    base_dir = Path(__file__).resolve().parents[1]
    cfg_file = base_dir / "secrets" / "send_email.txt"
    if not cfg_file.exists():
        return {}

    alias_map = {
        "host": "host",
        "hostname": "host",
        "server": "host",
        "smtp_host": "host",
        "mailhost": "host",
        "port": "port",
        "smtp_port": "port",
        "user": "user",
        "username": "user",
        "smtp_user": "user",
        "pass": "password",
        "passwd": "password",
        "password": "password",
        "smtp_password": "password",
        "from": "from",
        "from_addr": "from",
        "mail_from": "from",
        "smtp_from": "from",
        "tls": "starttls",
        "starttls": "starttls",
        "smtp_starttls": "starttls",
        "ssl": "ssl",
        "smtp_ssl": "ssl",
    }

    out: dict[str, str] = {}
    raw = cfg_file.read_text(encoding="utf-8", errors="ignore")
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
        if not key:
            continue

        mapped = alias_map.get(key)
        if mapped:
            out[mapped] = value

    return out


def _build_message(to: str, subject: str, body: str, from_addr: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def _find_sendmail() -> str | None:
    # Plesk/systemd-Umgebungen haben sendmail teils nicht im PATH.
    env_path = (os.getenv("PARKING_SENDMAIL_PATH") or "").strip()
    if env_path and Path(env_path).exists():
        return env_path

    which = shutil.which("sendmail")
    if which:
        return which

    for candidate in ("/usr/sbin/sendmail", "/usr/lib/sendmail", "/sbin/sendmail"):
        if Path(candidate).exists():
            return candidate

    return None


def _send_via_sendmail(msg: EmailMessage) -> bool:
    sendmail = _find_sendmail()
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
        port = int((cfg.get("port") or "25").strip())
    except ValueError:
        port = 25

    user = (cfg.get("user") or "").strip()
    password = cfg.get("password") or ""
    use_ssl = _parse_bool(cfg.get("ssl"), default=False)
    use_starttls = _parse_bool(cfg.get("starttls"), default=(not use_ssl and port in {587}))

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host=host, port=port, timeout=15) as smtp:
                smtp.ehlo()
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host=host, port=port, timeout=15) as smtp:
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
    # Standard-Absender (kann via Env oder send_email.txt überschrieben werden)
    default_from = "noreply@parkplatzportal.vr-365.de"

    cfg = _read_send_email_txt()
    from_addr = (
        os.getenv("PARKING_MAIL_FROM")
        or cfg.get("from")
        or default_from
    )

    msg = _build_message(to=to, subject=subject, body=body, from_addr=from_addr)

    # Projektregel clawyparken: kein STRATO-Pfad im Code.
    # Versandreihenfolge:
    # 1) Lokales sendmail (falls vorhanden)
    # 2) SMTP gemäß parking_app/secrets/send_email.txt (typisch lokaler Host/Relay)
    if _send_via_sendmail(msg):
        return

    if _send_via_smtp(msg, cfg):
        return

    raise RuntimeError("E-Mail-Versand fehlgeschlagen (weder sendmail noch SMTP-Konfiguration aus secrets/send_email.txt erfolgreich).")

# Parkplatz-Share (MVP)

Ziel: fixe Parkplätze (P01..P60) können von Ownern für Homeoffice-Tage angeboten werden; andere Mitarbeiter buchen tagesweise oder als Serie. Buchende können optional eine private (nicht dienstliche) E-Mail hinterlegen; dorthin gehen Buchungsbestätigung sowie Hinweise bei Owner-Storno/Änderungen.

## Start (dev)

```bash
cd /root/.openclaw/workspace
. .venv-parking/bin/activate
uvicorn parking_app.app.main:app --host 127.0.0.1 --port 18880
```

Dann im Browser: http://127.0.0.1:18880

## Daten
- SQLite DB: `parking_app/data/parking.sqlite3`
- Owner-Codes: `parking_app/secrets/owners.json` (chmod 600)

## E-Mail
Versand in diesem Projekt läuft ohne STRATO-Codepfad.

Versandreihenfolge:
1. Lokal via `sendmail` (Plesk-kompatibel), falls verfügbar
2. Fallback via SMTP-Konfiguration in `parking_app/secrets/send_email.txt`

Optionaler Absender:
- Env-Var: `PARKING_MAIL_FROM`
- oder `from` in `send_email.txt`
- Default: `noreply@parkplatzportal.vr-365.de`

Beispiel `parking_app/secrets/send_email.txt`:

```txt
host=127.0.0.1
port=25
user=
password=
from=noreply@parkplatzportal.vr-365.de
starttls=false
ssl=false
```

Unterstützte Schlüssel (auch als Aliase): `host/hostname/server`, `port`, `user/username`, `pass/password`, `from/from_addr`, `starttls/tls`, `ssl`.

## Nächste Schritte
- systemd service + nginx + HTTPS (nur nach Toby-Freigabe)
- UI polish (Kalenderansicht)

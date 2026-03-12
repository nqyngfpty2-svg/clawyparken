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
Versandpfad:
1. SMTP aus `parking_app/secrets/send_email.txt` (wenn konfiguriert)
2. Fallback lokal via `sendmail` (Plesk-kompatibel)

Absender:
- Env-Var `PARKING_MAIL_FROM` (höchste Priorität)
- sonst `from` aus `send_email.txt`
- sonst Fallback `noreply@localhost`

Beispiel `parking_app/secrets/send_email.txt`:

```txt
host=smtp.strato.de
port=587
user=noreply@parkplatzportal.vr-365.de
password=DEIN_PASSWORT
from=noreply@parkplatzportal.vr-365.de
starttls=true
ssl=false
```

## Datenschutz / Aufbewahrung
- Private Buchungs-E-Mails werden in `bookings.booker_email` gespeichert, solange sie für den Prozess nötig sind.
- Automatische Anonymisierung läuft beim App-Start:
  - Standard: nach **90 Tagen**
  - konfigurierbar über `PARKING_PRIVACY_RETENTION_DAYS`
- Bei Anonymisierung werden für alte Buchungen folgende Felder geleert: `booker_email`, `manage_token`, `cancel_reason`.
- Eine technische Kurzinfo ist unter `/privacy` verfügbar (für volle DSGVO-Infos um Betreiberangaben ergänzen).

## Nächste Schritte
- systemd service + nginx + HTTPS (nur nach Toby-Freigabe)
- UI polish (Kalenderansicht)

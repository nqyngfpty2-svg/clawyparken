# Parkplatz-Share (MVP)

Ziel: fixe Parkplätze (P01..P60) können von Ownern für Homeoffice-Tage angeboten werden; andere Mitarbeiter buchen tagesweise oder als Serie. Stornos durch Owner informieren den Buchenden per E-Mail.

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
Versand läuft über vorhandenes Script:
`email/strato_send.py`

## Nächste Schritte
- systemd service + nginx + HTTPS (nur nach Toby-Freigabe)
- UI polish (Kalenderansicht)

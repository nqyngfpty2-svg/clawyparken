# clawyparken – Parkplatzportal (MVP)

Kleine Webapp zum Teilen/Buchen von Firmenparkplätzen.

## Features (Stand MVP)
- Plätze P01–P60
- Owner-Code (4 Hex) pro Platz
- Owner kann Tage anbieten (einzeln + Serie) und Serien zurücknehmen
- Bucher bucht anonym (kein E-Mail, keine PII)
- Buchungscode = Link (/manage/<token>) zum Stornieren
- Parkplatzplan: interner Labeler (Klick-Tool) erzeugt nummeriertes Bild

## Lokaler Start (dev)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn parking_app.app.main:app --host 127.0.0.1 --port 18880
```

## Deployment (Beispiel)
- uvicorn via systemd (127.0.0.1:18880)
- nginx reverse proxy auf 443 (TLS: für IP self-signed, für Domain Let’s Encrypt)

## Wichtige Dateien
- App: `parking_app/app/main.py`
- Templates: `parking_app/templates/`

## Nicht im Repo
- Secrets, DB, Plan-PDF/Plan-PNG und generierte Annotierungen werden bewusst nicht versioniert.
  - Lege für deinen Parkplatzplan eine PNG-Datei unter `parking_app/plan/plan-1.png` ab.

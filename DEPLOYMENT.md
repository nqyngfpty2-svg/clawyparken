# Deployment (sauber, VPS)

Ziel: `parking_app` läuft als Service hinter nginx.

## 0) Voraussetzungen

- Ubuntu 24.04 (oder ähnlich)
- Python 3.12+
- `nginx`
- (optional) Domain + Let’s Encrypt

## 1) Repo auschecken

```bash
git clone <repo-url>
cd clawyparken
```

## 2) Python venv + Dependencies

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip wheel
pip install -r requirements.txt
```

## 3) Lokale Daten/Assets anlegen (nicht im Repo)

### 3.1 Owner-Codes
Beim ersten Start erzeugt die App automatisch Owner-Codes in:

- `parking_app/secrets/owners.json`

Diese Datei **nicht** committen.

### 3.2 Parkplatzplan
Lege deinen Plan als PNG ab:

- `parking_app/plan/plan-1.png`

(Die App liefert `/plan/raw.png` und erzeugt `/plan/annotated.png` aus den Klick-Labels.)

## Docker (Plesk-freundlich)

- Dockerfile ist im Repo.
- Anleitung: [deploy/plesk-docker.md](./deploy/plesk-docker.md)

## 4) Start (Dev)

```bash
make dev
```

Dann: http://127.0.0.1:18880

## 5) systemd Service (Prod)

### 5.1 Unit installieren

```bash
sudo cp deploy/systemd/parking-app.service /etc/systemd/system/parking-app.service
sudo systemctl daemon-reload
sudo systemctl enable --now parking-app
sudo systemctl status parking-app --no-pager
```

### 5.2 Logs

```bash
journalctl -u parking-app -f
```

## 6) nginx Reverse Proxy

### 6.1 Site aktivieren

```bash
sudo cp deploy/nginx/parking /etc/nginx/sites-available/parking
sudo ln -sf /etc/nginx/sites-available/parking /etc/nginx/sites-enabled/parking
sudo rm -f /etc/nginx/sites-enabled/default
sudo /usr/sbin/nginx -t
sudo systemctl restart nginx
```

### 6.2 TLS

- Für **IP-basiert**: self-signed Zertifikat (Browser-Warnung, aber ok für Tests).
- Für **Domain**: Let’s Encrypt (empfohlen).

Self-signed Beispiel:

```bash
sudo mkdir -p /etc/ssl/localcerts
sudo openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout /etc/ssl/localcerts/parking.key \
  -out /etc/ssl/localcerts/parking.crt \
  -subj "/CN=<VPS-IP-ODER-DOMAIN>"
sudo chmod 600 /etc/ssl/localcerts/parking.key
```

Dann in `deploy/nginx/parking` Pfade prüfen.

## 7) Firewall (UFW)

Wenn UFW aktiv ist, muss eingehend 443 (und optional 80 für ACME) offen sein:

```bash
sudo ufw allow 443/tcp
# sudo ufw allow 80/tcp
sudo ufw status verbose
```

## 8) Upgrade

```bash
git pull
make install
sudo systemctl restart parking-app
```

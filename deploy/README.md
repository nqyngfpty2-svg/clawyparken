# Deploy Quickstart (Copy/Paste)

> Ziel: clawyparken als Service hinter nginx auf einem VPS betreiben.

## 1) Checkout

```bash
sudo mkdir -p /opt/clawyparken
sudo chown $USER:$USER /opt/clawyparken
cd /opt/clawyparken

git clone <REPO_URL> .
```

## 2) Install

```bash
./scripts/install.sh
```

## 3) Plan-Asset ablegen

```bash
mkdir -p parking_app/plan
# Lege dein PNG hier ab:
# parking_app/plan/plan-1.png
```

## 4) systemd

```bash
sudo cp deploy/systemd/parking-app.service /etc/systemd/system/parking-app.service
sudo systemctl daemon-reload
sudo systemctl enable --now parking-app
sudo systemctl status parking-app --no-pager
```

## 5) nginx + TLS

Self-signed (IP-Test):

```bash
sudo apt-get update -y
sudo apt-get install -y nginx openssl

sudo mkdir -p /etc/ssl/localcerts
sudo openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout /etc/ssl/localcerts/parking.key \
  -out /etc/ssl/localcerts/parking.crt \
  -subj "/CN=<VPS-IP>"
sudo chmod 600 /etc/ssl/localcerts/parking.key

sudo cp deploy/nginx/parking /etc/nginx/sites-available/parking
sudo ln -sf /etc/nginx/sites-available/parking /etc/nginx/sites-enabled/parking
sudo rm -f /etc/nginx/sites-enabled/default
sudo /usr/sbin/nginx -t
sudo systemctl restart nginx
```

UFW:

```bash
sudo ufw allow 443/tcp
sudo ufw status verbose
```

## Logs

```bash
journalctl -u parking-app -f
```

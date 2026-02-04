# Plesk Docker Setup (ohne systemd, ohne Volume-Mapping-Frust)

Ziel: clawyparken läuft als Docker-Container. Plesk/nginx liefert die Domain aus (Reverse Proxy).

## A) Image in Plesk bauen

1) **Plesk → Docker** (für die Domain)
2) **Build** / **Build Image**
3) Als Build-Kontext den Ordner wählen, in dem das Repo liegt (wo `Dockerfile` liegt)
4) Image Name/Tag z.B. `clawyparken:latest`

## B) Container starten

1) In Plesk Docker: **Run** (aus dem gerade gebauten Image)
2) Port-Mapping:
   - Container-Port: `18880`
   - Host-Port: `18880` (oder einen freien Port, z.B. `18881`)
   - Wenn Plesk es anbietet: Host-IP auf **127.0.0.1** binden (best).

Nach Start testen:
- (auf dem Server) `curl http://127.0.0.1:18880/ | head`

## C) Persistente Daten (wichtig)

Damit Owner-Codes, DB und Plan-Labels nicht beim Container-Neustart verloren gehen, brauchst du Persistenz.

Du hast 2 Optionen:

### Option C1: Docker Volumes (empfohlen)
Binde folgende Pfade persistent:
- `/app/parking_app/data` (SQLite DB + plan_labels.json)
- `/app/parking_app/secrets` (owners.json + plan_admin_token)
- `/app/parking_app/plan` (dein plan-1.png)

Wenn du in Plesk Docker UI Volumes/Mounts setzen kannst:
- host dir → container dir (oder named volumes)

### Option C2: Bind Mounts auf einen Host-Pfad
Lege z.B. an:
- `/var/lib/clawyparken/data`
- `/var/lib/clawyparken/secrets`
- `/var/lib/clawyparken/plan`

und mounte:
- `/var/lib/clawyparken/data` → `/app/parking_app/data`
- `/var/lib/clawyparken/secrets` → `/app/parking_app/secrets`
- `/var/lib/clawyparken/plan` → `/app/parking_app/plan`

## D) Reverse Proxy (Domain → Container)

Plesk → **Apache & nginx-Einstellungen** → **Additional nginx directives**:

Wenn Host-Port = 18880:

```nginx
location / {
  proxy_pass http://127.0.0.1:18880;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
}
```

Wenn du Host-Port 18881 nutzt, entsprechend anpassen.

## E) Updates

1) `git pull` im Repo
2) In Plesk Docker: Image neu **Build**
3) Container neu starten (oder neu runnen)

## Troubleshooting

- **502 Bad Gateway**: Container läuft nicht / falscher Port.
  - Check: `curl http://127.0.0.1:18880/`
- **Owner-Codes/Labels weg nach Restart**: Persistenz (C) fehlt.

# Client Web Template (mit FastAPI und Tailwind)

Base project for small client portals:

- FastAPI
- Tailwind CSS
- SQLAlchemy (async)
- Jinja2 templates
- Docker / Docker Compose


## Vorgefertigte Ordner-Struktur mit Beispeil-Dateien:

```bash
projektname/
├─ app/
│  ├─ __init__.py          # leer
│  ├─ main.py              # FastAPI + Routen + Templates
│  ├─ db.py                # DB-Verbindung + Session
│  ├─ models.py            # SQLAlchemy-Models
│  ├─ logic.py             # Geschäftslogik / Helferfunktionen
│  ├─ templates/
│  │  ├─ base.html
│  │  └─ index.html
│  ├─ static/
│  │  └─ styles.css        # von Tailwind gebaut
│  └─ static_src/
│     └─ input.css         # Tailwind-Quelle
├─ Dockerfile
├─ docker-compose.prod.yml
├─ requirements.txt
├─ package.json
├─ tailwind.config.cjs
├─ .env.example
└─ .gitignore
```

## Local development
### für macOS / Linux

#### Python vorbereiten
```bash
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Tailwind vorbereiten
```bash
npm install
npm run dev   # startet Tailwind im Watch-Modus
```

#### App starten (mit automatischem Reload)
```bash
source venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app --reload-exclude "venv/*" --reload-exclude "**/__pycache__/*" --reload-exclude "*.pyc"
```

### für Windows

#### Python vorbereiten
```bash
python3.13 -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
```

#### Tailwind vorbereiten
```bash
npm install
npm run dev   # startet Tailwind im Watch-Modus
```

#### App starten (mit automatischem Reload)
```bash
.\venv\Scripts\Activate
uvicorn app.main:app --reload
```

Aufruf im Browser:
http://localhost:8000


### Optional: Lokales Docker-Testing (gleich auf Mac & Windows)

Falls du die App auch lokal als Docker-Container testen willst:

```bash
docker build -t local-app .
docker run -p 8000:8000 local-app
```

Aufruf im Browser:
http://localhost:8000

## In Portainer (Docker) deployen

1. Neuen Stack in Portainer anlegen
   - Name angeben (siehe IMAGE_NAME in .env + "stack" als suffix)
   - Build method = Repository
   - Authentication = AN
   - Username & Personal Access Token angeben
   - Repository URL angeben (.git als suffix nicht vergessen)
   - Repository reference = refs/heads/main
   - Compose path = docker-compose.yml (so lassen)
3. Deploy the stack klicken
4. App Container öffnen
5. Console öffnen
6. .env anlegen (muss im sleben Ordner sein wie der docker-compose.yml)
    ```bash
    nano .env
    ```
    .env befüllen siehe lokale .env oder .env.example
7. Container neustarten

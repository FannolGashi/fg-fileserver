# Gashi File Server

A lightweight self-hosted file server with upload, download, and public sharing support. Built with Python/Flask, served by Gunicorn, and packaged as a Docker container.

---

## Features

- Password-protected login
- Upload files via drag & drop or file picker
- Download and delete files
- Mark files as **public** (accessible without login) or **private**
- Public home page listing all public files
- Responsive UI (mobile friendly)
- File metadata stored as a simple JSON file — no database required

---

## How it is built

```
fileserver/
├── app.py                  # Flask application (routes, auth, file logic)
├── requirements.txt        # Python dependencies (Flask, Gunicorn, Werkzeug)
├── Dockerfile              # Container image definition
├── docker-compose.yml      # Service definition with port, volume, env vars
├── templates/
│   ├── login.html          # Login page
│   ├── home.html           # Public page (no login required)
│   └── index.html          # Admin file manager (login required)
└── uploads/                # Uploaded files (created automatically)
    └── .meta.json          # Tracks public/private state per file
```

**Stack:**
- **Flask** — handles HTTP routes, sessions, and templating (Jinja2)
- **Gunicorn** — production WSGI server (2 workers, 300s timeout)
- **Werkzeug** — secure filename handling
- **Docker** — containerised with a `python:3.12-slim` base image
- **Volumes** — `./uploads` is mounted from the host so files survive container restarts

---

## Deployment

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/) (included with Docker Desktop)

### 1. Clone or copy the project

```bash
git clone <your-repo-url> fileserver
cd fileserver
```

### 2. Configure credentials

Open `docker-compose.yml` and change the default values:

```yaml
environment:
  AUTH_USERNAME: admin           # Login username
  AUTH_PASSWORD: fileserver123   # Login password
  SECRET_KEY: change-me-to-a-random-string  # Flask session secret
  MAX_UPLOAD_MB: "500"           # Max upload size in MB
```

> **Important:** Always change `AUTH_PASSWORD` and `SECRET_KEY` before exposing the server publicly.

### 3. Start the container

```bash
docker compose up -d
```

The server will be available at `http://localhost:8181`.

### 4. Stop the server

```bash
docker compose down
```

---

## Rebuilding after changes

If you modify any source file, rebuild the image before restarting:

```bash
docker compose up -d --build
```

For a clean rebuild with no Docker layer cache:

```bash
docker compose build --no-cache && docker compose up -d
```

---

## Nginx reverse proxy (recommended for production)

If you put Nginx in front of the container, add these directives to your `location` block to allow large uploads and avoid timeout issues:

```nginx
location / {
    client_max_body_size 500M;
    proxy_pass http://localhost:8181;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
}
```

> Nginx's default `client_max_body_size` is 1MB. Without this, uploads larger than 1MB will be rejected by Nginx before they reach the app.

---

## Usage

### Public home page — `/`

Accessible by anyone without a login. Lists all files that have been marked as **public** with a download button.

### Admin login — `/login`

Log in with the configured username and password.

### File manager — `/manage`

Available after login. From here you can:

| Action | How |
|---|---|
| **Upload** | Drag & drop files onto the upload zone, or click *Choose files* |
| **Download** | Click the ↙ Download button on any file row |
| **Toggle public/private** | Click the 🌎 Public / 🔒 Private button — toggles instantly |
| **Delete** | Click the 🗑 button — confirms before deleting |

### Access control

| File state | Logged-in user | Anonymous user |
|---|---|---|
| Private | Can download | Redirected to login |
| Public | Can download | Can download from `/` |

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `AUTH_USERNAME` | `admin` | Login username |
| `AUTH_PASSWORD` | `fileserver123` | Login password |
| `SECRET_KEY` | *(random at start)* | Flask session signing key — set a fixed value so sessions survive restarts |
| `MAX_UPLOAD_MB` | `500` | Maximum upload size in megabytes |
| `UPLOAD_DIR` | `/uploads` | Path inside the container where files are stored |

---

## License

This project is licensed under the [MIT License](LICENSE).

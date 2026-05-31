import json
import os
import secrets
from pathlib import Path
from functools import wraps

from flask import (
    Flask, request, redirect, url_for, session,
    render_template, send_from_directory, flash, abort
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

USERNAME = os.environ.get("AUTH_USERNAME", "admin")
PASSWORD = os.environ.get("AUTH_PASSWORD", "fileserver123")
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/uploads"))
MAX_CONTENT_MB = int(os.environ.get("MAX_UPLOAD_MB", "500"))
META_FILE = UPLOAD_DIR / ".meta.json"

app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_MB * 1024 * 1024
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# --- Metadata helpers --------------------------------------------------------

def _load_meta() -> dict:
    if META_FILE.exists():
        try:
            return json.loads(META_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_meta(meta: dict) -> None:
    META_FILE.write_text(json.dumps(meta, indent=2))


def _is_public(filename: str) -> bool:
    return _load_meta().get(filename, {}).get("public", False)


def _set_public(filename: str, public: bool) -> None:
    meta = _load_meta()
    meta.setdefault(filename, {})["public"] = public
    _save_meta(meta)


def _clean_meta() -> None:
    """Remove metadata entries for files that no longer exist."""
    meta = _load_meta()
    existing = {p.name for p in UPLOAD_DIR.iterdir() if p.is_file() and p.name != ".meta.json"}
    cleaned = {k: v for k, v in meta.items() if k in existing}
    _save_meta(cleaned)


# --- Auth --------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# --- Routes ------------------------------------------------------------------

@app.route("/")
def home():
    """Public home — shows only files marked as public."""
    meta = _load_meta()
    files = []
    for p in sorted(UPLOAD_DIR.iterdir()):
        if p.is_file() and p.name != ".meta.json":
            if meta.get(p.name, {}).get("public"):
                files.append({"name": p.name, "size": _human_size(p.stat().st_size)})
    return render_template("home.html", files=files, logged_in=session.get("logged_in"))


@app.route("/manage")
@login_required
def index():
    meta = _load_meta()
    files = []
    for p in sorted(UPLOAD_DIR.iterdir()):
        if p.is_file() and p.name != ".meta.json":
            files.append({
                "name": p.name,
                "size": _human_size(p.stat().st_size),
                "public": meta.get(p.name, {}).get("public", False),
            })
    return render_template("index.html", files=files)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if (request.form.get("username") == USERNAME and
                request.form.get("password") == PASSWORD):
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Invalid credentials"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/upload", methods=["POST"])
@login_required
def upload():
    uploaded = request.files.getlist("files")
    if not uploaded or all(f.filename == "" for f in uploaded):
        flash("No files selected.", "error")
        return redirect(url_for("index"))
    saved = []
    for f in uploaded:
        if f.filename:
            name = secure_filename(f.filename)
            f.save(UPLOAD_DIR / name)
            saved.append(name)
    flash(f"Uploaded: {', '.join(saved)}", "success")
    return redirect(url_for("index"))


@app.route("/download/<filename>")
def download(filename):
    safe = secure_filename(filename)
    target = UPLOAD_DIR / safe
    if not target.is_file():
        abort(404)
    if not _is_public(safe) and not session.get("logged_in"):
        return redirect(url_for("login"))
    return send_from_directory(UPLOAD_DIR, safe, as_attachment=True)


@app.route("/toggle/<filename>", methods=["POST"])
@login_required
def toggle_public(filename):
    safe = secure_filename(filename)
    if not (UPLOAD_DIR / safe).is_file():
        abort(404)
    new_state = not _is_public(safe)
    _set_public(safe, new_state)
    state_label = "public" if new_state else "private"
    flash(f"{safe} is now {state_label}.", "success")
    return redirect(url_for("index"))


@app.route("/delete/<filename>", methods=["POST"])
@login_required
def delete(filename):
    safe = secure_filename(filename)
    target = UPLOAD_DIR / safe
    if target.is_file():
        target.unlink()
        _clean_meta()
        flash(f"Deleted: {safe}", "success")
    else:
        flash("File not found.", "error")
    return redirect(url_for("index"))


def _human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8181)

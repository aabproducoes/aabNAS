import os
from pathlib import Path
from flask import Flask, jsonify, request, send_file, abort, make_response

# Configure NAS_MEDIA_ROOT para a pasta compartilhada que deseja expor.
MEDIA_ROOT = Path(os.environ.get("NAS_MEDIA_ROOT", "/share/Media")).resolve()
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif"}
VIDEO_EXT = {".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi"}
app = Flask(__name__)

@app.after_request
def add_cors(response):
    origin = request.headers.get("Origin", "")
    if ALLOWED_ORIGIN == "*" or origin == ALLOWED_ORIGIN:
        response.headers["Access-Control-Allow-Origin"] = origin if origin else ALLOWED_ORIGIN
        response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Accept-Ranges"] = "bytes"
    return response

@app.route("/api/list", methods=["GET", "OPTIONS"])
def list_files():
    if request.method == "OPTIONS":
        return ("", 204)
    relative = request.args.get("path", "")
    folder = safe_path(relative)
    if not folder.is_dir():
        abort(404)
    items = []
    try:
        children = sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        for p in children:
            if p.name.startswith("."):
                continue
            if p.is_dir():
                items.append({"name": p.name, "type": "folder"})
            elif p.is_file():
                ext = p.suffix.lower()
                kind = "image" if ext in IMAGE_EXT else "video" if ext in VIDEO_EXT else None
                if kind:
                    items.append({"name": p.name, "type": kind, "size": p.stat().st_size})
    except PermissionError:
        abort(403)
    return jsonify({"path": relative.strip("/"), "items": items})

@app.route("/media/<path:relative>", methods=["GET", "OPTIONS"])
def media(relative):
    if request.method == "OPTIONS":
        return ("", 204)
    file_path = safe_path(relative)
    if not file_path.is_file() or file_path.suffix.lower() not in IMAGE_EXT | VIDEO_EXT:
        abort(404)
    # conditional=True permite suporte a Range, necessário para avançar em vídeos.
    return send_file(file_path, conditional=True, etag=True, max_age=3600)

def safe_path(relative):
    # Resolve caminhos e impede sair da pasta configurada (path traversal).
    candidate = (MEDIA_ROOT / relative).resolve()
    if candidate != MEDIA_ROOT and MEDIA_ROOT not in candidate.parents:
        abort(403)
    return candidate

if __name__ == "__main__":
    if not MEDIA_ROOT.exists():
        raise SystemExit(f"Pasta não encontrada: {MEDIA_ROOT}")
    # O Tailscale Serve encaminhará o acesso HTTPS para esta porta local.
    app.run(host="127.0.0.1", port=8765, threaded=True)

from email.parser import BytesParser
import json
import mimetypes
import os
from pathlib import Path
import re
import socketserver
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote
from uuid import uuid4


API_KEY = os.environ.get("API_KEY", "")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "uploads")).resolve()
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
PORT = int(os.environ.get("PORT", "8000"))


def clean_filename(name):
    name = Path(name or "file").name
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return name or "file"


def has_api_key(headers):
    bearer = headers.get("Authorization", "")
    if bearer.startswith("Bearer "):
        return bearer[len("Bearer "):] == API_KEY
    return headers.get("X-API-Key") == API_KEY


def parse_upload(headers, body):
    content_type = headers.get("Content-Type", "")
    if content_type.startswith("multipart/form-data"):
        raw = (
            "Content-Type: {}\r\nMIME-Version: 1.0\r\n\r\n".format(content_type).encode()
            + body
        )
        message = BytesParser().parsebytes(raw)
        for part in message.walk():
            if part.is_multipart():
                continue
            filename = part.get_filename()
            if filename:
                return clean_filename(filename), part.get_payload(decode=True) or b""
        raise ValueError("multipart field with filename is required")

    filename = headers.get("X-Filename")
    if not filename:
        raise ValueError("X-Filename header is required for raw uploads")
    return clean_filename(filename), body


def save_upload(filename, content):
    if not content:
        raise ValueError("empty upload")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored = "{}-{}".format(uuid4().hex, filename)
    path = UPLOAD_DIR / stored
    path.write_bytes(content)
    return stored, path


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            return self.send_json(200, {"ok": True})
        if self.path.startswith("/files/"):
            return self.send_file(self.path[len("/files/"):])
        self.send_error(404)

    def do_POST(self):
        if self.path != "/upload":
            return self.send_error(404)
        if not API_KEY:
            return self.send_json(500, {"error": "API_KEY is not set"})
        if not has_api_key(self.headers):
            return self.send_json(401, {"error": "invalid api key"})

        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return self.send_json(400, {"error": "empty body"})
        if length > MAX_UPLOAD_BYTES:
            return self.send_json(413, {"error": "file too large"})

        try:
            filename, content = parse_upload(self.headers, self.rfile.read(length))
            stored, path = save_upload(filename, content)
        except ValueError as exc:
            return self.send_json(400, {"error": str(exc)})

        url = "{}/files/{}".format(BASE_URL, stored)
        self.send_json(201, {"url": url, "filename": stored, "size": path.stat().st_size})

    def send_file(self, name):
        filename = clean_filename(unquote(name))
        path = (UPLOAD_DIR / filename).resolve()
        if path.parent != UPLOAD_DIR or not path.is_file():
            return self.send_error(404)

        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.end_headers()
        with path.open("rb") as file:
            chunk = file.read(1024 * 1024)
            while chunk:
                self.wfile.write(chunk)
                chunk = file.read(1024 * 1024)

    def send_json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print("listening on 0.0.0.0:{}, files in {}".format(PORT, UPLOAD_DIR))
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

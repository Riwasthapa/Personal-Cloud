import os
import hmac
import html
import base64
import secrets
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8080

# On your Mac, this is the local test storage.
STORAGE = Path.home() / "personal-cloud-data"

# Set these through environment variables before starting.
USERNAME = os.environ.get("CLOUD_USER", "admin")
PASSWORD = os.environ.get("CLOUD_PASSWORD", "")

MAX_UPLOAD = 100 * 1024 * 1024  # 100 MB per file

STORAGE.mkdir(parents=True, exist_ok=True)


class CloudHandler(BaseHTTPRequestHandler):

    def authenticated(self):
        header = self.headers.get("Authorization", "")

        if not header.startswith("Basic "):
            return False

        try:
            decoded = base64.b64decode(
                header[6:], validate=True
            ).decode("utf-8")
            username, password = decoded.split(":", 1)

            return (
                hmac.compare_digest(username, USERNAME)
                and hmac.compare_digest(password, PASSWORD)
            )
        except (ValueError, UnicodeDecodeError):
            return False

    def require_auth(self):
        if self.authenticated():
            return True

        self.send_response(401)
        self.send_header(
            "WWW-Authenticate",
            'Basic realm="Personal Cloud", charset="UTF-8"'
        )
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def respond(self, status, content):
        data = content.encode("utf-8")
        self.send_response(status)
        self.send_header(
            "Content-Type", "text/html; charset=utf-8"
        )
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def safe_path(self, relative=""):
        root = STORAGE.resolve()
        target = (root / relative).resolve()

        if not target.is_relative_to(root):
            raise ValueError("Invalid path")

        return target

    def page(self, title, body):
        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
* {{ box-sizing: border-box; }}
body {{
    max-width: 850px;
    margin: 35px auto;
    padding: 0 18px;
    font-family: system-ui, sans-serif;
    background: #111;
    color: #eee;
}}
section {{
    background: #1c1c1c;
    padding: 20px;
    margin: 18px 0;
    border-radius: 12px;
}}
a {{ color: #8ab4ff; }}
button, input {{
    padding: 10px;
    margin: 7px 0;
    max-width: 100%;
}}
button {{
    cursor: pointer;
    border: 0;
    border-radius: 6px;
}}
li {{
    padding: 10px 0;
    overflow-wrap: anywhere;
}}
small {{ color: #bbb; }}
</style>
</head>
<body>
{body}
</body>
</html>"""

    def do_GET(self):
        if not self.require_auth():
            return

        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/":
            relative = query.get("path", [""])[0]

            try:
                folder = self.safe_path(relative)

                if not folder.is_dir():
                    self.respond(404, "Folder not found")
                    return

                items = sorted(
                    folder.iterdir(),
                    key=lambda item: (
                        not item.is_dir(),
                        item.name.lower()
                    )
                )

                rows = []

                if relative:
                    parent = str(Path(relative).parent)
                    if parent == ".":
                        parent = ""
                    rows.append(
                        '<li><a href="/?path='
                        + quote(parent, safe="/")
                        + '">⬅ Parent folder</a></li>'
                    )

                for item in items:
                    name = item.name
                    escaped = html.escape(name)
                    rel = f"{relative}/{name}".strip("/")
                    encoded = quote(rel, safe="/")

                    if item.is_symlink():
                        continue

                    if item.is_dir():
                        rows.append(
                            f'<li>📁 <a href="/?path={encoded}">'
                            f'{escaped}/</a></li>'
                        )
                    elif item.is_file():
                        size = item.stat().st_size
                        rows.append(
                            f'<li>📄 {escaped} — {size:,} bytes '
                            f'<a href="/download?path={quote(rel, safe="/")}">'
                            f'Download</a></li>'
                        )

                body = f"""
<h1>My Personal Cloud</h1>
<p>Private file storage</p>
<section>
<h2>Upload a file</h2>
<input type="file" id="fileInput">
<br>
<button onclick="uploadFile()">Upload</button>
<p id="status"></p>
</section>
<section>
<h2>Files and folders</h2>
<p><small>Current folder: /{html.escape(relative)}</small></p>
<ul>{''.join(rows)}</ul>
</section>
<script>
async function uploadFile() {{
    const input = document.getElementById('fileInput');
    const status = document.getElementById('status');
    const file = input.files[0];

    if (!file) {{
        status.textContent = 'Choose a file first.';
        return;
    }}

    status.textContent = 'Uploading...';

    const currentPath = {relative!r};
    const url = '/upload?path=' + encodeURIComponent(currentPath)
        + '&name=' + encodeURIComponent(file.name);

    try {{
        const response = await fetch(url, {{
            method: 'POST',
            headers: {{'Content-Type': 'application/octet-stream'}},
            body: file
        }});

        status.textContent = response.ok
            ? 'Upload complete!'
            : 'Upload failed: ' + await response.text();

        if (response.ok) {{
            location.reload();
        }}
    }} catch (error) {{
        status.textContent = 'Upload failed. Check your connection.';
    }}
}}
</script>
"""
                self.respond(200, self.page("Personal Cloud", body))

            except (ValueError, OSError):
                self.respond(400, "Invalid folder path")

            return

        if parsed.path == "/download":
            relative = query.get("path", [""])[0]

            try:
                path = self.safe_path(relative)

                if path.is_symlink() or not path.is_file():
                    self.respond(404, "File not found")
                    return

                size = path.stat().st_size
                filename = quote(path.name)

                self.send_response(200)
                self.send_header(
                    "Content-Type", "application/octet-stream"
                )
                self.send_header(
                    "Content-Disposition",
                    f"attachment; filename*=UTF-8''{filename}"
                )
                self.send_header("Content-Length", str(size))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()

                with path.open("rb") as file:
                    while True:
                        chunk = file.read(65536)
                        if not chunk:
                            break
                        self.wfile.write(chunk)

            except (ValueError, OSError):
                self.respond(400, "Invalid file path")

            return

        self.respond(404, "Not found")

    def do_POST(self):
        if not self.require_auth():
            return

        parsed = urlparse(self.path)

        if parsed.path != "/upload":
            self.respond(404, "Not found")
            return

        query = parse_qs(parsed.query)
        relative = query.get("path", [""])[0]
        name = query.get("name", [""])[0]

        if (
            not name
            or name in (".", "..")
            or "/" in name
            or "\\" in name
            or "\x00" in name
        ):
            self.respond(400, "Invalid filename")
            return

        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1

        if length < 0 or length > MAX_UPLOAD:
            self.respond(413, "Upload must be 100 MB or smaller")
            return

        temporary = None

        try:
            folder = self.safe_path(relative)

            if not folder.is_dir():
                self.respond(400, "Invalid destination folder")
                return

            destination = self.safe_path(
                f"{relative}/{name}".strip("/")
            )

            if destination.is_symlink() or destination.is_dir():
                self.respond(400, "Invalid destination")
                return

            # Avoid overwriting an existing file.
            if destination.exists():
                self.respond(409, "A file with that name already exists")
                return

            temporary = folder / (
                ".upload-" + secrets.token_hex(12) + ".tmp"
            )

            remaining = length

            with temporary.open("xb") as output:
                while remaining:
                    chunk = self.rfile.read(min(65536, remaining))

                    if not chunk:
                        raise ConnectionError("Upload interrupted")

                    output.write(chunk)
                    remaining -= len(chunk)

            # Atomically create the final filename without overwriting.
            os.link(temporary, destination)
            temporary.unlink()
            temporary = None

            self.respond(201, "Upload successful")

        except FileExistsError:
            self.respond(409, "A file with that name already exists")
        except (ValueError, OSError, ConnectionError):
            self.respond(400, "Upload failed")

        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def log_message(self, fmt, *args):
        print("%s - %s" % (
            self.client_address[0],
            fmt % args
        ))


if __name__ == "__main__":
    if not PASSWORD:
        raise SystemExit(
            "Set CLOUD_PASSWORD before starting the server."
        )

    server = ThreadingHTTPServer((HOST, PORT), CloudHandler)
    print(f"Personal Cloud running at http://{HOST}:{PORT}")
    print(f"Local storage: {STORAGE}")
    server.serve_forever()
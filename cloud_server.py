import os
import hmac
import html
import base64
import secrets
import mimetypes
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime

HOST = os.environ.get("CLOUD_HOST", "127.0.0.1")
PORT = int(os.environ.get("CLOUD_PORT", "8080"))
STORAGE = Path(os.environ.get("CLOUD_STORAGE", str(Path.home() / "personal-cloud-data")))
USERNAME = os.environ.get("CLOUD_USER", "admin")
PASSWORD = os.environ.get("CLOUD_PASSWORD", "")
MAX_UPLOAD = 100 * 1024 * 1024
STORAGE.mkdir(parents=True, exist_ok=True)


def fmt_size(size):
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def icon_for(path):
    kind, _ = mimetypes.guess_type(path.name)
    if path.is_dir():
        return "📁"
    if kind:
        if kind.startswith("image/"): return "🖼️"
        if kind.startswith("video/"): return "🎬"
        if kind.startswith("audio/"): return "🎵"
        if kind == "application/pdf": return "📕"
        if kind.startswith("text/"): return "📄"
    return "📄"


CSS = r"""
:root{--bg:#f7f9fc;--surface:#fff;--ink:#202938;--muted:#697586;--line:#e5eaf1;--blue:#2563eb;--blue-soft:#eaf1ff;--sidebar:244px}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
button,input{font:inherit}button{cursor:pointer}a{color:inherit;text-decoration:none}
.sidebar{position:fixed;inset:0 auto 0 0;width:var(--sidebar);padding:22px 14px;background:#fff;border-right:1px solid var(--line);display:flex;flex-direction:column;z-index:5}
.brand{display:flex;align-items:center;gap:10px;font-size:19px;font-weight:800;padding:4px 10px 28px;letter-spacing:-.5px}
.brand-mark{width:35px;height:35px;border-radius:11px;background:linear-gradient(135deg,#4285f4,#2563eb);color:white;display:grid;place-items:center;font-size:20px}
.new-btn{display:flex;align-items:center;justify-content:center;gap:9px;background:#fff;border:1px solid var(--line);box-shadow:0 2px 5px #17255412;border-radius:12px;padding:12px;font-weight:700;margin:0 7px 23px}
.nav-label{font-size:10px;color:#9aa3b2;font-weight:800;letter-spacing:1.2px;padding:12px 14px 7px}
.nav{display:flex;align-items:center;gap:12px;padding:11px 14px;margin:2px 0;border-radius:10px;color:#505b6b;font-weight:550}
.nav:hover{background:#f4f7fb}.nav.active{background:var(--blue-soft);color:#174ea6;font-weight:750}.nav-icon{width:20px;text-align:center;font-size:17px}
.side-bottom{margin-top:auto}.storage-box{margin:18px 8px 8px;padding:14px 12px;border:1px solid var(--line);border-radius:12px}
.storage-title{display:flex;justify-content:space-between;gap:5px;font-weight:700;font-size:12px;margin-bottom:10px}
.progress{height:6px;background:#e9edf5;border-radius:20px;overflow:hidden}.progress span{display:block;height:100%;background:#4285f4;border-radius:20px}
.storage-note{font-size:11px;color:var(--muted);margin-top:8px}
.main{margin-left:var(--sidebar);min-height:100vh}.topbar{height:74px;background:#fff;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:16px;padding:0 32px;position:sticky;top:0;z-index:4}
.search{max-width:680px;flex:1;position:relative}.search input{width:100%;background:#f1f4f9;border:1px solid transparent;border-radius:12px;padding:13px 16px 13px 42px;outline:none}
.search input:focus{background:#fff;border-color:#b8cdf9;box-shadow:0 0 0 3px #2563eb12}.search-icon{position:absolute;left:14px;top:11px;color:#6b7280;font-size:19px}
.top-actions{margin-left:auto;display:flex;align-items:center;gap:9px}.primary,.secondary,.icon-btn{border:0;border-radius:9px;padding:10px 13px;font-weight:700}
.primary{background:var(--blue);color:#fff}.primary:hover{background:#1d4ed8}.secondary{background:#fff;border:1px solid var(--line);color:#344054}
.avatar{width:34px;height:34px;border-radius:50%;background:#dbeafe;color:#1d4ed8;display:grid;place-items:center;font-weight:800}
.content{padding:30px 34px 52px;max-width:1500px;margin:auto}.eyebrow{color:#64748b;font-size:11px;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;margin:0 0 8px}
.heading-row{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;margin-bottom:25px}h1{font-size:29px;line-height:1.2;letter-spacing:-.9px;margin:0 0 8px}.subtitle{color:var(--muted);margin:0}
.actions{display:flex;gap:9px;flex-wrap:wrap}.storage-banner{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:21px 23px;background:linear-gradient(110deg,#eaf2ff,#f3f7ff 65%,#fff);border:1px solid #dce8ff;border-radius:16px;margin-bottom:30px}
.banner-left{display:flex;align-items:center;gap:14px}.banner-icon{width:47px;height:47px;border-radius:13px;background:#d8e7ff;display:grid;place-items:center;font-size:23px}
.banner-title{font-weight:800;font-size:15px;margin-bottom:4px}.banner-sub{color:#667085;font-size:12px}.banner-meter{width:min(270px,42%);min-width:130px}
.meter-top{display:flex;justify-content:space-between;font-size:12px;font-weight:700;margin-bottom:8px}
.section{margin:0 0 30px}.section-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 14px}h2{font-size:17px;letter-spacing:-.25px;margin:0}.muted{color:var(--muted);font-size:12px}
.folder-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.folder-card{display:flex;align-items:center;gap:12px;background:#fff;border:1px solid var(--line);border-radius:12px;padding:15px;min-width:0;transition:box-shadow .15s,border .15s}
.folder-card:hover,.file-card:hover{border-color:#c8d8fb;box-shadow:0 5px 16px #1e3a8a0c}.folder-icon{width:41px;height:41px;display:grid;place-items:center;background:#eef4ff;border-radius:11px;font-size:22px;flex-shrink:0}
.folder-name{font-weight:750;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.folder-meta{font-size:11px;color:var(--muted);margin-top:3px}
.toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}.view-switch{display:flex;gap:3px;background:#fff;border:1px solid var(--line);padding:3px;border-radius:9px}
.view-switch button{border:0;border-radius:6px;padding:6px 9px;background:transparent;color:#687386}.view-switch button.active{background:var(--blue-soft);color:#174ea6}
.file-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px}.file-card{background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden;min-width:0;transition:box-shadow .15s,border .15s}
.file-preview{height:132px;background:#f1f5fb;display:grid;place-items:center;font-size:42px;position:relative}.file-preview img{width:100%;height:100%;object-fit:cover}
.file-type{position:absolute;left:9px;top:9px;background:#ffffffdf;border-radius:6px;padding:4px 6px;font-size:9px;font-weight:800;color:#465268}
.file-info{padding:12px 12px 10px}.file-name{font-weight:750;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:5px}.file-meta{font-size:11px;color:var(--muted);display:flex;justify-content:space-between;gap:6px}
.file-actions{display:flex;align-items:center;gap:6px;padding:0 12px 12px}.file-actions a,.file-actions button{font-size:11px;padding:6px 8px;border-radius:7px;border:1px solid var(--line);background:#fff;color:#475467}.file-actions .delete{color:#b42318}
.file-list{display:none;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}.list-row{display:grid;grid-template-columns:minmax(180px,2fr) 1fr 1fr auto;align-items:center;gap:12px;padding:12px 15px;border-bottom:1px solid #eef0f4}.list-row:last-child{border-bottom:0}
.list-head{background:#f8fafc;color:#687386;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.5px}.list-name{display:flex;align-items:center;gap:10px;min-width:0}.list-name span:last-child{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:650}
.empty{padding:43px 20px;text-align:center;background:#fff;border:1px dashed #d5dce7;border-radius:13px;color:var(--muted)}.empty-icon{font-size:34px;margin-bottom:10px}
.notice{margin:0 0 15px;padding:11px 14px;border-radius:9px;background:#eff6ff;color:#1d4ed8;display:none}dialog{border:0;border-radius:15px;padding:24px;width:min(420px,calc(100% - 28px));box-shadow:0 24px 80px #10182835}dialog::backdrop{background:#10182880}
dialog h3{margin:0 0 8px;font-size:19px}dialog p{color:#667085;line-height:1.55}.dialog-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:22px}.danger{background:#c62828;color:#fff}
#dropZone{border:1px dashed #aabce0;background:#f7faff;border-radius:12px;padding:17px;text-align:center;color:#64748b;display:none;margin-bottom:17px}
body.list-mode .file-grid{display:none}body.list-mode .file-list{display:block}
@media(max-width:1150px){.folder-grid,.file-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.content{padding:26px 24px}}
@media(max-width:850px){:root{--sidebar:70px}.sidebar{padding:17px 8px}.brand{padding:4px 9px 24px}.brand-name,.nav-label,.nav-text,.new-label,.storage-box{display:none}.new-btn{margin:0 3px 21px;padding:12px 0}.nav{justify-content:center;padding:12px 0}.nav-icon{font-size:19px}.topbar{padding:0 16px}.content{padding:23px 17px}.folder-grid,.file-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.topbar{height:64px;gap:8px;padding:0 10px}.top-actions .secondary{display:none}.top-actions .primary{padding:10px}.content{padding:20px 11px}.heading-row{display:block}.heading-row .actions{margin-top:14px}.storage-banner{align-items:flex-start;flex-direction:column;padding:16px}.banner-meter{width:100%}.folder-grid,.file-grid{gap:8px}.folder-card{padding:10px;gap:8px}.folder-icon{width:34px;height:34px;font-size:18px}.file-preview{height:98px}.file-info{padding:9px}.file-actions{padding:0 9px 9px}.list-row{grid-template-columns:minmax(130px,2fr) auto;gap:7px}.list-row>*:nth-child(2),.list-row>*:nth-child(3){display:none}h1{font-size:25px}.search input{padding-left:34px;font-size:12px}.search-icon{left:10px}}
"""


class CloudHandler(BaseHTTPRequestHandler):
    def authenticated(self):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header[6:], validate=True).decode("utf-8")
            username, password = decoded.split(":", 1)
            return hmac.compare_digest(username, USERNAME) and hmac.compare_digest(password, PASSWORD)
        except (ValueError, UnicodeDecodeError):
            return False

    def require_auth(self):
        if self.authenticated():
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Personal Cloud", charset="UTF-8"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def respond(self, status, content, content_type="text/html; charset=utf-8"):
        data = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
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
        return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light"><title>{html.escape(title)} · Personal Cloud</title>
<style>{CSS}</style></head><body>{body}</body></html>"""

    def do_GET(self):
        if not self.require_auth():
            return
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/":
            relative = query.get("path", [""])[0]
            try:
                folder = self.safe_path(relative)
                if folder.is_symlink() or not folder.is_dir():
                    self.respond(404, "Folder not found")
                    return

                children = []
                for item in folder.iterdir():
                    if item.is_symlink() or item.name.startswith(".upload-") or item.name.endswith(".tmp"):
                        continue
                    try:
                        if item.is_dir() or item.is_file():
                            children.append(item)
                    except OSError:
                        continue
                children.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
                folders = [p for p in children if p.is_dir()]
                files = [p for p in children if p.is_file()]
                total_bytes = sum(p.stat().st_size for p in STORAGE.rglob("*") if p.is_file() and not p.is_symlink())
                used = fmt_size(total_bytes)
                pct = min(100, total_bytes / (5 * 1024**3) * 100)

                folder_cards = []
                for item in folders:
                    rel = f"{relative}/{item.name}".strip("/")
                    count = sum(1 for p in item.iterdir() if not p.is_symlink() and not p.name.startswith(".upload-"))
                    folder_cards.append(
                        f'<a class="folder-card" href="/?path={quote(rel, safe="/")}" data-folder-name="{html.escape(item.name.lower(), quote=True)}">'
                        f'<span class="folder-icon">📁</span><span style="min-width:0"><span class="folder-name" style="display:block">{html.escape(item.name)}</span>'
                        f'<span class="folder-meta">{count} item{"s" if count != 1 else ""}</span></span></a>'
                    )

                file_cards, list_rows = [], []
                for item in files:
                    name = item.name
                    escaped = html.escape(name)
                    rel = f"{relative}/{name}".strip("/")
                    encoded = quote(rel, safe="/")
                    size = item.stat().st_size
                    modified = datetime.fromtimestamp(item.stat().st_mtime).strftime("%d %b %Y")
                    kind, _ = mimetypes.guess_type(name)
                    group = "image" if kind and kind.startswith("image/") else "video" if kind and kind.startswith("video/") else "document" if kind and (kind.startswith("text/") or kind == "application/pdf" or "word" in kind or "spreadsheet" in kind) else "other"
                    icon = icon_for(item)
                    preview = f'<img src="/preview?path={encoded}" alt="" loading="lazy">' if group == "image" else f'<span>{icon}</span>'
                    # JSON encoding makes names with apostrophes safe in the inline JS arguments.
                    import json
                    js_rel, js_name = json.dumps(rel), json.dumps(name)
                    file_cards.append(
                        f'<article class="file-card" data-file-name="{html.escape(name.lower(), quote=True)}" data-kind="{group}">'
                        f'<div class="file-preview">{preview}<span class="file-type">{group.upper()}</span></div>'
                        f'<div class="file-info"><div class="file-name" title="{escaped}">{escaped}</div>'
                        f'<div class="file-meta"><span>{fmt_size(size)}</span><span>{modified}</span></div></div>'
                        f'<div class="file-actions"><a href="/download?path={encoded}">↓ Download</a>'
                        f'<button class="delete" onclick="askDelete({html.escape(js_rel)},{html.escape(js_name)})">Delete</button></div></article>'
                    )
                    list_rows.append(
                        f'<div class="list-row" data-file-name="{html.escape(name.lower(), quote=True)}" data-kind="{group}">'
                        f'<span class="list-name"><span>{icon}</span><span title="{escaped}">{escaped}</span></span>'
                        f'<span>{fmt_size(size)}</span><span>{modified}</span>'
                        f'<span class="file-actions"><a href="/download?path={encoded}">Download</a>'
                        f'<button class="delete" onclick="askDelete({html.escape(js_rel)},{html.escape(js_name)})">Delete</button></span></div>'
                    )

                parent_link = ""
                if relative:
                    parent = str(Path(relative).parent)
                    if parent == ".": parent = ""
                    parent_link = f'<a class="secondary" href="/?path={quote(parent, safe="/")}">← Back</a>'
                title = html.escape(relative) if relative else "Home"
                body = f"""
<div class="sidebar">
<a class="brand" href="/"><span class="brand-mark">☁</span><span class="brand-name">Personal Cloud</span></a>
<button class="new-btn" onclick="openCreate()"><span>＋</span><span class="new-label">New</span></button>
<div class="nav-label">WORKSPACE</div>
<a class="nav active" href="/"><span class="nav-icon">⌂</span><span class="nav-text">Home</span></a>
<a class="nav" href="/?path="><span class="nav-icon">▣</span><span class="nav-text">My Files</span></a>
<a class="nav" href="#" onclick="filterRecent(event)"><span class="nav-icon">◷</span><span class="nav-text">Recent</span></a>
<a class="nav" href="#" onclick="filterStarred(event)"><span class="nav-icon">☆</span><span class="nav-text">Starred</span></a>
<div class="nav-label">CATEGORIES</div>
<a class="nav" href="#" onclick="filterType(event,'image')"><span class="nav-icon">▧</span><span class="nav-text">Photos</span></a>
<a class="nav" href="#" onclick="filterType(event,'video')"><span class="nav-icon">▷</span><span class="nav-text">Videos</span></a>
<a class="nav" href="#" onclick="filterType(event,'document')"><span class="nav-icon">▤</span><span class="nav-text">Documents</span></a>
<div class="side-bottom"><a class="nav" href="#" onclick="showAll(event)"><span class="nav-icon">⌕</span><span class="nav-text">Show all files</span></a>
<div class="storage-box"><div class="storage-title"><span>Storage used</span><span>{used}</span></div><div class="progress"><span style="width:{pct:.1f}%"></span></div><div class="storage-note">Cloud folder usage · 5 GB visual guide</div></div></div>
</div>
<main class="main"><header class="topbar"><div class="search"><span class="search-icon">⌕</span><input id="searchInput" type="search" placeholder="Search files and folders" autocomplete="off" aria-label="Search files and folders"></div>
<div class="top-actions"><button class="secondary" onclick="document.getElementById('fileInput').click()">＋ Upload</button><button class="primary" onclick="openCreate()">＋ New folder</button><div class="avatar" title="Personal Cloud">PC</div></div></header>
<div class="content"><div class="heading-row"><div><p class="eyebrow">YOUR PRIVATE SPACE</p><h1>{'Welcome to your cloud' if not relative else title}</h1><p class="subtitle">Your files, organized and accessible from your devices.</p></div><div class="actions">{parent_link}<button class="secondary" onclick="document.getElementById('fileInput').click()">⬆ Upload files</button></div></div>
<div class="storage-banner"><div class="banner-left"><div class="banner-icon">☁</div><div>
<section class="section"><div class="section-head"><div><h2>Folders</h2><div class="muted">Jump into your spaces</div></div><button class="secondary" onclick="openCreate()">＋ New folder</button></div><div class="folder-grid" id="folderGrid">{''.join(folder_cards) or '<div class="muted">No folders in this location yet.</div>'}</div></section>
<section class="section"><div class="toolbar"><div><h2 id="filesTitle">Files</h2><div class="muted" id="fileCount">{len(files)} files in /{html.escape(relative) if relative else ''}</div></div><div class="view-switch"><button id="gridBtn" class="active" onclick="setView('grid')" title="Grid view">▦</button><button id="listBtn" onclick="setView('list')" title="List view">☷</button></div></div>
<div class="file-grid" id="fileGrid">{''.join(file_cards)}</div><div class="file-list" id="fileList"><div class="list-row list-head"><span>Name</span><span>Size</span><span>Modified</span><span>Actions</span></div>{''.join(list_rows)}</div>
<div class="empty" id="emptyState" style="display:{'none' if files else 'block'}"><div class="empty-icon">☁</div><strong>This folder has no files yet</strong><p>Upload a file or create a folder to get started.</p><button class="primary" onclick="document.getElementById('fileInput').click()">Upload a file</button></div></section>
<input id="fileInput" type="file" multiple hidden><div id="uploadStatus" class="muted" role="status" style="margin-top:14px"></div></div></main>
<dialog id="createDialog"><h3>Create a folder</h3><p>Choose a name for your new folder.</p><input id="folderName" type="text" placeholder="e.g. Work documents" style="width:100%;padding:12px;border:1px solid #d0d5dd;border-radius:9px"><div class="dialog-actions"><button class="secondary" onclick="closeCreate()">Cancel</button><button class="primary" onclick="createFolder()">Create folder</button></div></dialog>
<dialog id="deleteDialog"><h3>Delete this file?</h3><p id="deleteMessage">This action cannot be undone.</p><div class="dialog-actions"><button class="secondary" onclick="document.getElementById('deleteDialog').close()">Cancel</button><button class="primary danger" id="confirmDelete">Delete file</button></div></dialog>
<script>
const currentPath = {relative!r}; let pendingDelete = null;
function setView(v){{document.body.classList.toggle('list-mode',v==='list');document.getElementById('gridBtn').classList.toggle('active',v==='grid');document.getElementById('listBtn').classList.toggle('active',v==='list');try{{localStorage.setItem('pc-view',v)}}catch(_ ){{}}}}
try{{if(localStorage.getItem('pc-view')==='list')setView('list')}}catch(_ ){{}}
function filterCards(test,title){{let shown=0;document.querySelectorAll('[data-file-name]').forEach(el=>{{const m=test(el);el.style.display=m?'':'none';if(m&&el.classList.contains('file-card'))shown++}});document.getElementById('filesTitle').textContent=title;document.getElementById('emptyState').style.display=shown?'none':'block';document.getElementById('fileCount').textContent=shown+' matching files'}}
document.getElementById('searchInput').addEventListener('input',e=>{{const q=e.target.value.trim().toLowerCase();filterCards(el=>(el.dataset.fileName||'').includes(q),q?'Search results':'Files')}});
function filterType(e,t){{e.preventDefault();document.getElementById('searchInput').value='';filterCards(el=>el.dataset.kind===t,t==='image'?'Photos':t==='video'?'Videos':'Documents')}}
function filterRecent(e){{e.preventDefault();document.getElementById('searchInput').value='';filterCards(()=>true,'Recent files')}}
function filterStarred(e){{e.preventDefault();showNotice('Starred files are not available yet; we can add this in a later version.')}}
function showAll(e){{e.preventDefault();document.getElementById('searchInput').value='';filterCards(()=>true,'Files')}}
function showNotice(m){{const n=document.getElementById('notice');n.textContent=m;n.style.display='block'}}
function openCreate(){{document.getElementById('folderName').value='';document.getElementById('createDialog').showModal()}}
function closeCreate(){{document.getElementById('createDialog').close()}}
async function createFolder(){{const n=document.getElementById('folderName').value.trim();if(!n)return;try{{const r=await fetch('/mkdir?path='+encodeURIComponent(currentPath)+'&name='+encodeURIComponent(n),{{method:'POST'}});if(!r.ok){{alert(await r.text());return}}location.reload()}}catch(_){{alert('Could not create folder. Check your connection.')}}}}
function askDelete(p,n){{pendingDelete=p;document.getElementById('deleteMessage').textContent='“'+n+'” will be permanently deleted from your cloud storage.';document.getElementById('deleteDialog').showModal()}}
document.getElementById('confirmDelete').addEventListener('click',async()=>{{if(!pendingDelete)return;const b=document.getElementById('confirmDelete');b.disabled=true;try{{const r=await fetch('/delete?path='+encodeURIComponent(pendingDelete),{{method:'POST'}});if(!r.ok){{alert(await r.text());return}}location.reload()}}catch(_){{alert('Could not delete file. Check your connection.')}}finally{{b.disabled=false;pendingDelete=null}}}});
async function uploadFiles(files){{const status=document.getElementById('uploadStatus');if(!files.length)return;let ok=0,errors=[];status.textContent='Uploading '+files.length+' file(s)…';for(const f of files){{try{{const r=await fetch('/upload?path='+encodeURIComponent(currentPath)+'&name='+encodeURIComponent(f.name),{{method:'POST',headers:{{'Content-Type':'application/octet-stream'}},body:f}});if(!r.ok)throw Error(f.name+': '+await r.text());ok++}}catch(e){{errors.push(e.message)}}}}status.textContent=ok+' uploaded'+(errors.length?'; '+errors.join(' | '):'')+'.';if(ok)setTimeout(()=>location.reload(),errors.length?1800:500)}}
document.getElementById('fileInput').addEventListener('change',e=>{{uploadFiles(Array.from(e.target.files||[]));e.target.value=''}});
document.addEventListener('dragover',e=>{{e.preventDefault();document.getElementById('dropZone').style.display='block'}});
document.addEventListener('dragleave',e=>{{if(e.clientX===0&&e.clientY===0)document.getElementById('dropZone').style.display='none'}});
document.addEventListener('drop',e=>{{e.preventDefault();document.getElementById('dropZone').style.display='none';uploadFiles(Array.from(e.dataTransfer.files||[]))}});
</script>"""
                self.respond(200, self.page("Personal Cloud", body))
            except (ValueError, OSError):
                self.respond(400, "Invalid folder path")
            return

        if parsed.path == "/download":
            try:
                path = self.safe_path(query.get("path", [""])[0])
                if path.is_symlink() or not path.is_file():
                    self.respond(404, "File not found")
                    return
                size = path.stat().st_size
                filename = quote(path.name)
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{filename}")
                self.send_header("Content-Length", str(size))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                with path.open("rb") as file:
                    while True:
                        chunk = file.read(65536)
                        if not chunk: break
                        self.wfile.write(chunk)
            except (ValueError, OSError):
                self.respond(400, "Invalid file path")
            return

        if parsed.path == "/preview":
            try:
                path = self.safe_path(query.get("path", [""])[0])
                kind, _ = mimetypes.guess_type(path.name)
                if path.is_symlink() or not path.is_file() or not kind or not kind.startswith("image/"):
                    self.respond(404, "Preview not found")
                    return
                data = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
            except (ValueError, OSError):
                self.respond(400, "Invalid preview path")
            return
        self.respond(404, "Not found")

    def do_POST(self):
        if not self.require_auth():
            return
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        relative = query.get("path", [""])[0]

        if parsed.path == "/mkdir":
            name = query.get("name", [""])[0].strip()
            if not name or name in (".", "..") or "/" in name or "\\" in name or "\x00" in name or name.startswith(".upload-"):
                self.respond(400, "Invalid folder name")
                return
            try:
                folder = self.safe_path(relative)
                if not folder.is_dir():
                    self.respond(400, "Invalid destination folder")
                    return
                destination = self.safe_path(f"{relative}/{name}".strip("/"))
                destination.mkdir()
                self.respond(201, "Folder created")
            except FileExistsError:
                self.respond(409, "A file or folder with that name already exists")
            except (ValueError, OSError):
                self.respond(400, "Could not create folder")
            return

        if parsed.path == "/delete":
            try:
                target = self.safe_path(relative)
                if target == STORAGE.resolve():
                    self.respond(400, "Cannot delete the cloud root")
                    return
                if target.is_symlink() or not target.is_file():
                    self.respond(400, "Only files can be deleted in this version")
                    return
                target.unlink()
                self.respond(200, "File deleted")
            except (ValueError, OSError):
                self.respond(400, "Could not delete file")
            return

        if parsed.path != "/upload":
            self.respond(404, "Not found")
            return
        name = query.get("name", [""])[0]
        if not name or name in (".", "..") or "/" in name or "\\" in name or "\x00" in name or name.startswith(".upload-"):
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
        destination = None
        created_destination = False
        try:
            folder = self.safe_path(relative)
            if not folder.is_dir():
                self.respond(400, "Invalid destination folder")
                return
            destination = self.safe_path(f"{relative}/{name}".strip("/"))
            if destination.is_symlink() or destination.is_dir():
                self.respond(400, "Invalid destination")
                return
            if destination.exists():
                self.respond(409, "A file with that name already exists")
                return
            temporary = folder / (".upload-" + secrets.token_hex(12) + ".tmp")
            remaining = length
            with temporary.open("xb") as output:
                while remaining:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        raise ConnectionError("Upload interrupted")
                    output.write(chunk)
                    remaining -= len(chunk)
            with destination.open("xb") as output:
                created_destination = True
                with temporary.open("rb") as source:
                    while True:
                        chunk = source.read(65536)
                        if not chunk: break
                        output.write(chunk)
            temporary.unlink()
            temporary = None
            self.respond(201, "Upload successful")
        except FileExistsError:
            self.respond(409, "A file with that name already exists")
        except (ValueError, OSError, ConnectionError):
            if created_destination and destination is not None:
                try: destination.unlink(missing_ok=True)
                except OSError: pass
            self.respond(400, "Upload failed")
        finally:
            if temporary is not None:
                try: temporary.unlink(missing_ok=True)
                except OSError: pass

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.client_address[0], fmt % args))


if __name__ == "__main__":
    if not PASSWORD:
        raise SystemExit("Set CLOUD_PASSWORD before starting the server.")
    server = ThreadingHTTPServer((HOST, PORT), CloudHandler)
    print(f"Personal Cloud running at http://{HOST}:{PORT}")
    print(f"Local storage: {STORAGE}")
    server.serve_forever()


from pathlib import Path
from datetime import datetime
import shutil

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.urls import reverse
from .forms import FileUploadForm


def get_cloud_files():
    folder = Path(settings.ANDROID_MEDIA_ROOT)
    folder.mkdir(parents=True, exist_ok=True)

    files = []

    for path in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
        if (
            path.is_file() and not path.name.startswith(".") and path.suffix.lower() in {
            ".jpg", ".jpeg", ".png", ".webp", ".gif"
            }
        ):
            stat = path.stat()
            files.append({
                "name": path.name,
                "file_size": stat.st_size,
                "uploaded_at": datetime.fromtimestamp(stat.st_mtime),
                "url": reverse("cloud_file", kwargs={"filename": path.name}),
            })

    return files


def _upload_context(form):
    storage_dir = Path(settings.ANDROID_MEDIA_ROOT)
    storage_dir.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(storage_dir)

    return {
        "form": form,
        "available_storage_bytes": usage.free,
        "storage_used_percent": (
            round(usage.used / usage.total * 100) if usage.total else 0
        ),
    }


@login_required
def upload_file(request):
    if request.method == "POST":
        form = FileUploadForm(request.POST, request.FILES)

        if form.is_valid():
            folder = Path(settings.ANDROID_MEDIA_ROOT)
            folder.mkdir(parents=True, exist_ok=True)

            uploads = [
                (uploaded, folder / Path(uploaded.name.replace("\\", "/")).name)
                for uploaded in form.cleaned_data["files"]
            ]
            names = [destination.name for _, destination in uploads]

            if len(names) != len(set(names)) or any(
                destination.exists() for _, destination in uploads
            ):
                form.add_error("files", "A file with that name already exists.")
                return render(
                    request,
                    "storage/upload.html",
                    _upload_context(form),
                )

            for uploaded, destination in uploads:
                with destination.open("xb") as output:
                    for chunk in uploaded.chunks():
                        output.write(chunk)

            return redirect("home")

    else:
        form = FileUploadForm()

    return render(
        request,
        "storage/upload.html",
        _upload_context(form),
    )


@login_required
def cloud_file(request, filename):
    folder = Path(settings.ANDROID_MEDIA_ROOT)
    path = folder / Path(filename).name

    if Path(filename).name != filename or not path.is_file():
        raise Http404("File not found")

    return FileResponse(path.open("rb"))


@login_required
@require_POST
def download_file(request, filename):
    folder = Path(settings.ANDROID_MEDIA_ROOT)
    path = folder / Path(filename).name

    if Path(filename).name != filename or not path.is_file():
        raise Http404("File not found")

    return FileResponse(
        path.open("rb"),
        as_attachment=True,
        filename=path.name,
    )


@login_required
@require_POST
def delete_file(request, filename):
    folder = Path(settings.ANDROID_MEDIA_ROOT)
    path = folder / Path(filename).name

    if Path(filename).name != filename or not path.is_file():
        raise Http404("File not found")

    path.unlink()
    return redirect("home")

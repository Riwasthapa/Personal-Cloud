
from pathlib import Path
from datetime import datetime
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
        if path.is_file() and path.suffix.lower() in {
            ".jpg", ".jpeg", ".png", ".webp", ".gif"
        }:
            stat = path.stat()
            files.append({
                "name": path.name,
                "file_size": stat.st_size,
                "uploaded_at": datetime.fromtimestamp(stat.st_mtime),
                "url": reverse("cloud_file", kwargs={"filename": path.name}),
            })

    return files


@login_required
def upload_file(request):
    if request.method == "POST":
        form = FileUploadForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded = request.FILES["file"]
            folder = Path(settings.ANDROID_MEDIA_ROOT)
            folder.mkdir(parents=True, exist_ok=True)

            destination = folder / Path(uploaded.name).name

            # Avoid overwriting an existing image.
            if destination.exists():
                return render(request, "storage/upload.html", {
                    "form": form,
                    "error": "A file with that name already exists.",
                })

            with destination.open("wb") as output:
                for chunk in uploaded.chunks():
                    output.write(chunk)

            return redirect("home")

    else:
        form = FileUploadForm()

    return render(request, "storage/upload.html", {"form": form})


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

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import FileUploadForm, File
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.views.decorators.http import require_POST
import shutil
from pathlib import Path
from django.conf import settings

@login_required
def upload_file(request):

    if request.method == 'POST':
        form = FileUploadForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            uploaded_file = form.save(commit=False)

            uploaded_file.owner = request.user
            uploaded_file.original_name = request.FILES['file'].name
            uploaded_file.file_size = request.FILES['file'].size

            uploaded_file.save()

            source_path = Path(uploaded_file.file.path)
            destination_dir = settings.ANDROID_MEDIA_ROOT

            destination_dir.mkdir(parents=True, exist_ok=True)

            destination_path = destination_dir / uploaded_file.original_name

            shutil.copy2(source_path, destination_path)
            return redirect('home')

    else:
        form = FileUploadForm()

    return render(request, 'storage/upload.html', {
        'form': form
    })


@login_required
def download_file(request, file_id):

    file = get_object_or_404(
        File,
        id=file_id,
        owner=request.user
    )

    return FileResponse(
        file.file.open('rb'),
        as_attachment=True,
        filename=file.original_name
    )


@login_required
@require_POST
def delete_file(request, file_id):

    file = get_object_or_404(
        File,
        id=file_id,
        owner=request.user
    )

    file.file.delete(save=False)
    file.delete()

    return redirect('home')


import shutil
from datetime import date, timedelta

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings

from storage.views import get_cloud_files


@login_required
def home(request):
    files = get_cloud_files()

    # Sort newest files first
    files.sort(key=lambda f: f['uploaded_at'], reverse=True)

    # Group files by upload date
    grouped_files = {}

    for file in files:
        upload_date = file['uploaded_at'].date()
        grouped_files.setdefault(upload_date, []).append(file)

    today = date.today()
    yesterday = today - timedelta(days=1)

    file_groups = []

    for upload_date, group in grouped_files.items():

        if upload_date == today:
            heading = "Today"
        elif upload_date == yesterday:
            heading = "Yesterday"
        else:
            heading = upload_date.strftime("%B %d, %Y")

        file_groups.append({
            'heading': heading,
            'date': upload_date,
            'files': group,
        })

    storage_usage = shutil.disk_usage(settings.ANDROID_MEDIA_ROOT)

    available_storage_bytes = storage_usage.free

    storage_used_percent = (
        round(storage_usage.used / storage_usage.total * 100)
        if storage_usage.total
        else 0
    )

    return render(request, 'dashboard/home.html', {
        'files': files,
        'file_groups': file_groups,
        'available_storage_bytes': available_storage_bytes,
        'storage_used_percent': storage_used_percent,
    })

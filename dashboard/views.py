
import shutil

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings

from storage.views import get_cloud_files


@login_required
def home(request):
    files = get_cloud_files()
    storage_usage = shutil.disk_usage(settings.ANDROID_MEDIA_ROOT)
    available_storage_bytes = storage_usage.free
    storage_used_percent = (
        round(storage_usage.used / storage_usage.total * 100)
        if storage_usage.total
        else 0
    )

    return render(request, 'dashboard/home.html', {
        'files': files,
        'available_storage_bytes': available_storage_bytes,
        'storage_used_percent': storage_used_percent,
    })

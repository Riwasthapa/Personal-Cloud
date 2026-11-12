
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from storage.views import get_cloud_files


@login_required
def home(request):
    files = get_cloud_files()

    return render(request, 'dashboard/home.html', {
        'files': files
    })

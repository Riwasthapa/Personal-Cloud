from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from storage.models import File


@login_required
def home(request):

    files = File.objects.filter(
        owner=request.user
    ).order_by('-uploaded_at')

    return render(request, 'dashboard/home.html', {
        'files': files
    })
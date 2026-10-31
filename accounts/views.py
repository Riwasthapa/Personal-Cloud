from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from .forms import RegistrationForm, LoginForm
from django.contrib.auth import authenticate, login, logout


User = get_user_model()


def register(request):

    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)

            password = form.cleaned_data['password']
            user.set_password(password)

            user.save()

            return redirect('login')

    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {
        'form': form
    })



def user_login(request):

    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            user = authenticate(
                request,
                email=email,
                password=password
            )

            if user is not None:
                login(request, user)
                return redirect('home')

            form.add_error(
                None,
                'Invalid email or password.'
            )

    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {
        'form': form
    })

def user_logout(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')

    return redirect('home')
# apps/users/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm  # ← use your custom form

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to E-Shop.')
            return redirect('core:home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect(request.GET.get('next') or 'core:home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

@login_required
def user_logout(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been logged out.')
        return redirect('core:home')
    return redirect('core:home')

@login_required
def profile(request):
    return render(request, 'users/profile.html', {})
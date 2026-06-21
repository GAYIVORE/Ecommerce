# apps/users/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings  # ← Safe enterprise settings accessor

from .forms import RegisterForm

# Cryptographic token processing variables
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail

User = get_user_model()


def get_redirect_url_for_user(user):
    """
    Context helper to instantly route accounts by clearanced marketplace status tier.
    """
    if user.is_authenticated and user.is_vendor:
        return 'products:vendor_dashboard'
    return 'core:home'


def register(request):
    if request.user.is_authenticated:
        return redirect(get_redirect_url_for_user(request.user))
        
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Flag user inactive until cryptographic token transaction is authorized
            user = form.save(commit=False)
            user.is_active = False  
            user.save()
            
            # Serialize signing keys
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Formulate full domain callback token endpoint pathing
            activation_url = f"http://{request.get_host()}/users/activate/{uid}/{token}/"
            
            subject = "Activate your E-Shop Account"
            message = f"Hi {user.username},\n\nPlease click the link below to verify your account:\n{activation_url}"
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                messages.info(request, 'Account created! Please check your email to activate your account.')
                return render(request, 'users/check_email.html')
            except Exception as e:
                # Fallback safeguard: Purge incomplete user entry if the mail daemon fails completely
                user.delete()
                print("SMTP Error details:", e)
                messages.error(request, 'System was unable to dispatch authentication receipt. Registration aborted.')
        else:
            messages.error(request, 'Please adjust the highlighted data anomalies below.')
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
        
    # Check if user exists and token is valid BEFORE setting backend
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        
        # Set the backend here, only when we are sure we have a valid user
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        
        login(request, user)
        messages.success(request, f'Email verified! Welcome to the marketplace, {user.username}.')
        return redirect(get_redirect_url_for_user(user))
    else:
        messages.error(request, 'The activation link is invalid or has expired.')
        return render(request, 'users/activation_failed.html')

        
def user_login(request):
    if request.user.is_authenticated:
        return redirect(get_redirect_url_for_user(request.user))

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            
            # Check for next param or fall back to conditional user landing layout routing
            next_param = request.GET.get('next')
            if next_param:
                return redirect(next_param)
            return redirect(get_redirect_url_for_user(user))
        else:
            messages.error(request, 'Invalid username or password credentials.')
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})


@login_required
def user_logout(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been logged out.')
    return redirect('users:login')


@login_required
def profile(request):
    return render(request, 'users/profile.html', {})
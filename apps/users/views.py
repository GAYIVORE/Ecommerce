# apps/users/views.py

import logging

from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings  # ← Safe enterprise settings accessor
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import RegisterForm
from apps.core.utils import get_client_ip, record_attempt, clear_attempts, is_rate_limited

# Cryptographic token processing variables
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail

User = get_user_model()
logger = logging.getLogger(__name__)

# --- Brute-force protection thresholds -------------------------------------
# Login: locked out after this many failed attempts, tracked separately by IP
# and by the submitted username/email so an attacker can't dodge the limit by
# spraying many usernames from one IP, or many IPs at one target account.
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_WINDOW_MINUTES = 15
# Registration: throttled per IP to blunt automated mass account creation.
REGISTER_ATTEMPT_LIMIT = 5
REGISTER_ATTEMPT_WINDOW_MINUTES = 60


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
        # 🔒 Throttle registration submissions per IP to blunt bots/scripts mass-
        # creating accounts. Every POST counts against the limit (not just failed
        # ones) since a successful flood of real-looking signups is the actual
        # abuse case, not just invalid ones.
        client_ip = get_client_ip(request)
        register_key = f"register-ip:{client_ip}"
        if is_rate_limited(register_key, REGISTER_ATTEMPT_LIMIT, REGISTER_ATTEMPT_WINDOW_MINUTES):
            messages.error(
                request,
                "Too many signup attempts from this location. Please try again in a bit."
            )
            return render(request, 'users/register.html', {'form': RegisterForm()})

        record_attempt(register_key)
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Flag user inactive until cryptographic token transaction is authorized
            user = form.save(commit=False)
            user.is_active = False  
            user.save()
            
            # Serialize signing keys
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Formulate full domain callback token endpoint pathing. Uses the
            # request's actual scheme (http locally, https in production
            # behind the proxy) instead of a hardcoded "http://", which would
            # otherwise send users a broken/insecure link once deployed.
            activation_url = request.build_absolute_uri(f"/users/activate/{uid}/{token}/")
            
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
                logger.error("Failed to send account activation email: %s", e, exc_info=True)
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
        client_ip = get_client_ip(request)
        submitted_username = request.POST.get('username', '').strip().lower()
        ip_key = f"login-ip:{client_ip}"
        # Keyed by the *submitted* identifier (not a resolved user id) so this
        # also throttles guessing usernames that don't exist, without needing
        # a DB lookup first.
        user_key = f"login-user:{submitted_username}" if submitted_username else None

        # 🔒 Brute-force protection: lock out further attempts once either the
        # source IP or the targeted account has racked up too many recent
        # failures. Checking both independently stops both "one IP spraying
        # many accounts" and "many IPs hammering one account" attack shapes.
        if is_rate_limited(ip_key, LOGIN_ATTEMPT_LIMIT, LOGIN_ATTEMPT_WINDOW_MINUTES) or (
            user_key and is_rate_limited(user_key, LOGIN_ATTEMPT_LIMIT, LOGIN_ATTEMPT_WINDOW_MINUTES)
        ):
            messages.error(
                request,
                "Too many login attempts. Please wait a few minutes before trying again."
            )
            return render(request, 'users/login.html', {'form': AuthenticationForm()})

        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")

            # Successful login: clear this identifier/IP's failed-attempt history
            # so a legitimate user isn't left one bad guess away from lockout.
            clear_attempts(ip_key)
            if user_key:
                clear_attempts(user_key)

            # Check for next param or fall back to conditional user landing layout routing.
            # 🔒 Security fix: previously this redirected straight to whatever "next" value
            # was in the querystring, which is a classic open-redirect vulnerability — an
            # attacker could send a link like /users/login/?next=https://evil.com and, after
            # a real login, users would be bounced to an attacker-controlled site. We now
            # validate the target is a relative/same-host URL before trusting it.
            next_param = request.GET.get('next')
            if next_param and url_has_allowed_host_and_scheme(
                url=next_param,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_param)
            return redirect(get_redirect_url_for_user(user))
        else:
            record_attempt(ip_key)
            if user_key:
                record_attempt(user_key)
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
    """
    Handles rendering user profile metadata and saving incoming 
    profile picture files instantly upon user mutation.
    """
    if request.method == 'POST':
        if 'profile_picture' in request.FILES:
            request.user.profile_picture = request.FILES['profile_picture']
            request.user.save()
            messages.success(request, 'Your profile avatar has been successfully updated!')
            return redirect('users:profile')
            
    return render(request, 'users/profile.html')
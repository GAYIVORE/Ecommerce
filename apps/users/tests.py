# apps/users/tests.py
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, Client
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.core.models import RateLimitAttempt
from .views import LOGIN_ATTEMPT_LIMIT, REGISTER_ATTEMPT_LIMIT

User = get_user_model()


class RegistrationTests(TestCase):
    def test_register_creates_inactive_user_and_sends_activation_email(self):
        response = self.client.post(reverse('users:register'), {
            'username': 'newbie',
            'email': 'newbie@example.com',
            'password1': 'a-strong-password-123',
            'password2': 'a-strong-password-123',
        })
        self.assertEqual(response.status_code, 200)  # renders check_email.html
        user = User.objects.get(username='newbie')
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('activate', mail.outbox[0].body)

    def test_register_rejects_mismatched_passwords(self):
        response = self.client.post(reverse('users:register'), {
            'username': 'oops',
            'email': 'oops@example.com',
            'password1': 'a-strong-password-123',
            'password2': 'a-different-password-456',
        })
        self.assertFalse(User.objects.filter(username='oops').exists())
        self.assertEqual(response.status_code, 200)

    def test_register_is_rate_limited_per_ip(self):
        for i in range(REGISTER_ATTEMPT_LIMIT):
            self.client.post(reverse('users:register'), {
                'username': f'user{i}',
                'email': f'user{i}@example.com',
                'password1': 'a-strong-password-123',
                'password2': 'a-strong-password-123',
            }, REMOTE_ADDR='1.1.1.1')

        response = self.client.post(reverse('users:register'), {
            'username': 'oneTooMany',
            'email': 'oneTooMany@example.com',
            'password1': 'a-strong-password-123',
            'password2': 'a-strong-password-123',
        }, REMOTE_ADDR='1.1.1.1', follow=True)

        self.assertFalse(User.objects.filter(username='oneTooMany').exists())
        self.assertContains(response, 'Too many signup attempts')


class ActivationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='pending', email='pending@example.com', password='pass12345', is_active=False
        )

    def _activation_url(self, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        return reverse('users:activate', args=[uid, token])

    def test_valid_token_activates_and_logs_in(self):
        response = self.client.get(self._activation_url(self.user), follow=True)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(response.context['user'].is_authenticated)

    def test_invalid_token_does_not_activate(self):
        url = reverse('users:activate', args=[
            urlsafe_base64_encode(force_bytes(self.user.pk)), 'bad-token'
        ])
        self.client.get(url)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', email='alice@example.com', password='correct-horse')

    def test_correct_credentials_log_in(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'alice', 'password': 'correct-horse'
        })
        self.assertRedirects(response, reverse('core:home'))

    def test_wrong_password_does_not_log_in(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'alice', 'password': 'wrong'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_open_redirect_is_blocked(self):
        """
        🔒 Regression test for the open-redirect fix: ?next= pointing off-site
        must never be honored, even after a legitimate login.
        """
        response = self.client.post(
            reverse('users:login') + '?next=https://evil.example.com/phish',
            {'username': 'alice', 'password': 'correct-horse'},
        )
        self.assertNotEqual(response.url, 'https://evil.example.com/phish')
        self.assertRedirects(response, reverse('core:home'))

    def test_same_site_next_is_honored(self):
        response = self.client.post(
            reverse('users:login') + '?next=/users/profile/',
            {'username': 'alice', 'password': 'correct-horse'},
        )
        self.assertRedirects(response, '/users/profile/')

    def test_lockout_after_repeated_failures(self):
        for _ in range(LOGIN_ATTEMPT_LIMIT):
            self.client.post(reverse('users:login'), {'username': 'alice', 'password': 'wrong'})

        # Even the *correct* password is now blocked until the window passes.
        response = self.client.post(
            reverse('users:login'), {'username': 'alice', 'password': 'correct-horse'}, follow=True
        )
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertContains(response, 'Too many login attempts')

    def test_successful_login_clears_failed_attempt_history(self):
        self.client.post(reverse('users:login'), {'username': 'alice', 'password': 'wrong'})
        self.client.post(reverse('users:login'), {'username': 'alice', 'password': 'correct-horse'})
        self.assertFalse(RateLimitAttempt.objects.filter(key='login-user:alice').exists())

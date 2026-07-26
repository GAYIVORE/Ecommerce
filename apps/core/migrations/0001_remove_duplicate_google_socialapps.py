from django.db import migrations


def remove_duplicate_google_socialapps(apps, schema_editor):
    """
    Delete any Google SocialApp rows stored in the database.

    Google OAuth in this project is configured entirely through env vars
    (GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET) via
    SOCIALACCOUNT_PROVIDERS['google']['APPS'] in settings. django-allauth
    merges any settings-based apps with SocialApp rows already stored in
    the database for the same provider. If a SocialApp row for 'google'
    was ever created (e.g. via /admin/), the settings-based app and the
    DB row both match provider='google', and allauth's get_app() raises
    MultipleObjectsReturned on every page that renders the login button,
    instead of picking one.

    Since credentials are managed via env vars, any DB rows for this
    provider are redundant and safe to remove.
    """
    SocialApp = apps.get_model('socialaccount', 'SocialApp')
    SocialApp.objects.filter(provider='google').delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('socialaccount', '0006_alter_socialaccount_extra_data'),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_google_socialapps, migrations.RunPython.noop),
    ]
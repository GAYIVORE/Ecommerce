# Generated manually for delivery-window fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0003_shop_phone_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='shop',
            name='min_delivery_days',
            field=models.PositiveSmallIntegerField(
                default=2,
                help_text="Soonest a customer could realistically receive an order after you ship it.",
                verbose_name="Fastest delivery (days)",
            ),
        ),
        migrations.AddField(
            model_name='shop',
            name='max_delivery_days',
            field=models.PositiveSmallIntegerField(
                default=5,
                help_text="Worst-case delivery time to set with customers, including packing time.",
                verbose_name="Slowest delivery (days)",
            ),
        ),
    ]

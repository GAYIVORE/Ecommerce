# Generated manually for vendor delivery-window snapshot + fulfillment timeline

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_order_orders_user_orderdate_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='suborder',
            name='estimated_delivery_start',
            field=models.DateField(blank=True, null=True, verbose_name='Estimated Delivery — Earliest'),
        ),
        migrations.AddField(
            model_name='suborder',
            name='estimated_delivery_end',
            field=models.DateField(blank=True, null=True, verbose_name='Estimated Delivery — Latest'),
        ),
        migrations.AddField(
            model_name='suborder',
            name='shipped_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Shipped At'),
        ),
        migrations.AddField(
            model_name='suborder',
            name='delivered_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Delivered At'),
        ),
        migrations.AddIndex(
            model_name='suborder',
            index=models.Index(fields=['shop', 'status'], name='orders_subo_shop_status_idx'),
        ),
        migrations.AddIndex(
            model_name='suborder',
            index=models.Index(fields=['status'], name='orders_subo_status_idx'),
        ),
    ]

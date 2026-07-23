from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.orders.models import Order
from apps.orders.views import restore_order_stock


class Command(BaseCommand):
    """
    Releases stock reserved by unpaid Paystack orders that never completed —
    the customer abandoned checkout, closed the tab before the redirect back,
    and no webhook ever arrived. Without this, that stock stays locked up
    forever since place_order() reserves it immediately at checkout time.

    Intended to run on a schedule (cron / Vercel Cron / hosting platform's
    scheduled tasks) every 15-30 minutes, e.g.:

        */30 * * * * cd /path/to/project && python manage.py expire_stale_orders

    Usage:
        python manage.py expire_stale_orders                 # default: 2 hour cutoff
        python manage.py expire_stale_orders --hours 1        # custom cutoff
        python manage.py expire_stale_orders --dry-run         # preview only
    """
    help = "Cancels stale unpaid Paystack orders and restores their reserved stock."

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=float, default=2.0,
                             help='Orders older than this many hours (default: 2) are expired.')
        parser.add_argument('--dry-run', action='store_true',
                             help='List what would be expired without changing anything.')

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=options['hours'])

        stale_orders = Order.objects.filter(
            payment_method='paystack',
            payment_status=False,
            order_date__lt=cutoff,
        ).exclude(status='Cancelled')

        count = stale_orders.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No stale unpaid orders found."))
            return

        if options['dry_run']:
            for order in stale_orders:
                self.stdout.write(f"Would expire order #{order.id} (placed {order.order_date})")
            self.stdout.write(self.style.WARNING(f"{count} order(s) would be expired. (dry run, no changes made)"))
            return

        expired = 0
        for order in stale_orders:
            restore_order_stock(order)
            expired += 1
            self.stdout.write(f"Expired order #{order.id} and restored its reserved stock.")

        self.stdout.write(self.style.SUCCESS(f"Done — {expired} stale order(s) expired."))

from decimal import Decimal

from django.db.models import Sum

from .models import EarningTransaction


def get_user_balance(user):
    """Available balance = sum of every COMPLETED transaction (credits and withdrawals)."""
    total = EarningTransaction.objects.filter(
        user=user, status=EarningTransaction.Status.COMPLETED
    ).aggregate(Sum('amount'))['amount__sum']
    return total or Decimal('0.00')

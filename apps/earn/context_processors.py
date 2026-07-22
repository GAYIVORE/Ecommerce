from decimal import Decimal

from .utils import get_user_balance


def earn_balance_processor(request):
    """Exposes the logged-in user's Earn wallet balance to every template (nav pill)."""
    if request.user.is_authenticated:
        return {'nav_balance': get_user_balance(request.user)}
    return {'nav_balance': Decimal('0.00')}

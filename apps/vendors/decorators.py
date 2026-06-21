# apps/vendors/decorators.py

from django.core.exceptions import PermissionDenied
from functools import wraps

def vendor_required(view_func):
    """
    🔐 Security Guard: Restricts dashboard routing endpoints strictly to 
    accounts approved by a platform administrator (User.is_vendor == True).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and getattr(request.user, 'is_vendor', False):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Access Denied. Your account has not been approved as a marketplace vendor.")
    return _wrapped_view
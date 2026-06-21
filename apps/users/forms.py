from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class RegisterForm(UserCreationForm):
    """
    Public profile registration form. Forcefully restricts public self-assignment 
    of security clearanced roles (VENDOR, ADMIN). Every signup defaults 
    automatically to a baseline CUSTOMER.
    """
    class Meta:
        model = User
        # Removed 'role' from fields to prevent public tamper vulnerability
        fields = ['username', 'email', 'phone_number', 'marketing_opt_in']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Inject standard utility framework styles for elegant Tailwind CSS rendering
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500/20'
                })
            else:
                field.widget.attrs.update({
                    'class': 'block w-full rounded-xl border-slate-200 bg-white p-3 text-sm text-slate-800 placeholder:text-slate-400 focus:border-amber-500 focus:ring focus:ring-amber-500/10'
                })
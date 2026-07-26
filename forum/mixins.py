from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect


class VerifiedRequiredMixin(AccessMixin):
    """Requiere autenticación Y verificación del email.
    - anónimo          → redirect a login con ?next=
    - no verificado    → redirect a /cuenta/verificar/
    - verificado       → pasa
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_verified:
            return redirect("forum:verify_waiting")
        return super().dispatch(request, *args, **kwargs)

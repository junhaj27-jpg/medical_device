from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import PasswordChangeDoneView, PasswordChangeView
from django.urls import reverse_lazy

from apps.audit.models import AuditLog


class SecurePasswordChangeView(PasswordChangeView):
    template_name = "accounts/password_change_form.html"
    success_url = reverse_lazy("password_change_done")

    def form_valid(self, form):
        response = super().form_valid(form)
        update_session_auth_hash(self.request, form.user)
        AuditLog.objects.create(
            user=self.request.user,
            action="PASSWORD_CHANGED",
            model_name="accounts.User",
            object_id=str(self.request.user.pk),
            object_repr=self.request.user.get_username(),
            after_data={"event": "비밀번호 변경 완료"},
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )
        return response


class SecurePasswordChangeDoneView(PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import PasswordChangeDoneView, PasswordChangeView
from django.urls import reverse_lazy

from apps.audit.services import record_audit


class SecurePasswordChangeView(PasswordChangeView):
    template_name = "accounts/password_change_form.html"
    success_url = reverse_lazy("password_change_done")

    def form_valid(self, form):
        response = super().form_valid(form)
        update_session_auth_hash(self.request, form.user)
        record_audit(
            user=self.request.user, target=self.request.user,
            action="PASSWORD_CHANGED",
            after={"event": "비밀번호 변경 완료"},
            reason="사용자 비밀번호 변경", request=self.request,
        )
        return response


class SecurePasswordChangeDoneView(PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"

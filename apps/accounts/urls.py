from django.urls import path

from .views import SecurePasswordChangeDoneView, SecurePasswordChangeView

urlpatterns = [
    path("password/change/", SecurePasswordChangeView.as_view(), name="password_change"),
    path("password/change/done/", SecurePasswordChangeDoneView.as_view(), name="password_change_done"),
]

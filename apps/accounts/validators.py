import re

from django.contrib.auth.password_validation import (
    CommonPasswordValidator,
    MinimumLengthValidator,
    UserAttributeSimilarityValidator,
)
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class KoreanMinimumLengthValidator(MinimumLengthValidator):
    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _("비밀번호는 최소 %(min_length)d자 이상이어야 합니다."),
                code="password_too_short",
                params={"min_length": self.min_length},
            )


class KoreanUserAttributeSimilarityValidator(UserAttributeSimilarityValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                _("비밀번호는 사용자명이나 개인정보와 지나치게 비슷할 수 없습니다."),
                code="password_too_similar",
            ) from None


class KoreanCommonPasswordValidator(CommonPasswordValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                _("너무 흔하게 사용되는 비밀번호입니다. 다른 비밀번호를 사용해 주세요."),
                code="password_too_common",
            ) from None


class PasswordComplexityValidator:
    patterns = (
        (r"[A-Z]", "영문 대문자"),
        (r"[a-z]", "영문 소문자"),
        (r"[0-9]", "숫자"),
        (r"[^A-Za-z0-9]", "특수문자"),
    )

    def validate(self, password, user=None):
        missing = [label for pattern, label in self.patterns if not re.search(pattern, password)]
        if missing:
            raise ValidationError(
                _("비밀번호에 다음 항목이 필요합니다: %(requirements)s."),
                code="password_missing_complexity",
                params={"requirements": ", ".join(missing)},
            )

    def get_help_text(self):
        return _("영문 대문자, 영문 소문자, 숫자, 특수문자를 각각 1개 이상 포함해야 합니다.")

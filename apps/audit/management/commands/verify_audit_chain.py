from django.core.management.base import BaseCommand, CommandError

from apps.audit.services import verify_audit_chain


class Command(BaseCommand):
    help = "감사 로그 HMAC 해시 체인의 무결성을 검증합니다."

    def handle(self, *args, **options):
        errors = verify_audit_chain()
        if errors:
            raise CommandError(f"변조 또는 체인 단절 감사 로그: {errors}")
        self.stdout.write(self.style.SUCCESS("감사 로그 해시 체인이 유효합니다."))

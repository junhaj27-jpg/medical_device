from django.core.management.base import BaseCommand, CommandError

from apps.audit.key_providers import get_key_provider
from apps.audit.services import verify_audit_chain_detailed


class Command(BaseCommand):
    help="활성 감사 키와 과거 로그 검증 키의 가용성을 점검합니다. 키 원문은 출력하지 않습니다."
    def handle(self,*args,**options):
        provider=get_key_provider(); active=provider.active(); results=verify_audit_chain_detailed()
        missing=sorted({r["key_id"] for r in results if r["status"]=="KEY_UNAVAILABLE"})
        invalid=[r["id"] for r in results if r["status"]=="INVALID"]
        if missing: raise CommandError(f"검증 키를 사용할 수 없는 key_id: {', '.join(missing)}")
        if invalid: raise CommandError(f"무결성 검증 실패 로그 ID: {invalid}")
        self.stdout.write(self.style.SUCCESS(f"활성 key_id={active.key_id}; 과거 로그 검증 가능"))

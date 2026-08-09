from django.conf import settings
from django.core.management.base import BaseCommand

from apps.audit.exporters import LocalJSONLExporter
from apps.audit.outbox_services import process_outbox_batch


class Command(BaseCommand):
    help="대기 중인 감사 outbox를 로컬 JSONL exporter로 전송합니다. 로컬 exporter는 WORM이 아닙니다."
    def add_arguments(self,parser): parser.add_argument("--limit",type=int,default=100)
    def handle(self,*args,**options):
        events=process_outbox_batch(LocalJSONLExporter(settings.AUDIT_JSONL_EXPORT_PATH),limit=options["limit"]); self.stdout.write(f"processed={len(events)}")

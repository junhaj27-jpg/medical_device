from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.adverse_events.models import AdverseEvent
from apps.audit.services import record_audit


class Command(BaseCommand):
    help="기한 초과 이상사례를 확인하고 감사 로그에 기록합니다."
    def handle(self,*args,**options):
        qs=AdverseEvent.objects.filter(due_date__lt=timezone.localdate()).exclude(status="CLOSED")
        for event in qs:
            if not event.is_overdue: event.is_overdue=True; event.save(update_fields=["is_overdue"])
            record_audit(user=None,action="OVERDUE_CHECK",target=event,after={"due_date":str(event.due_date)},reason="자동 기한 점검")
        self.stdout.write(self.style.SUCCESS(f"기한 초과 {qs.count()}건 확인"))

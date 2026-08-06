from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.adverse_events.models import AdverseEvent
from apps.audit.models import AuditLog
class Command(BaseCommand):
    help="기한 초과 이상사례를 확인하고 감사 로그에 기록합니다."
    def handle(self,*args,**options):
        qs=AdverseEvent.objects.filter(due_date__lt=timezone.localdate()).exclude(status="CLOSED")
        for event in qs:
            if not event.is_overdue: event.is_overdue=True; event.save(update_fields=["is_overdue"])
            AuditLog.objects.create(action="OVERDUE_CHECK",model_name="AdverseEvent",object_id=str(event.pk),object_repr=event.event_number,after_data={"due_date":str(event.due_date)})
        self.stdout.write(self.style.SUCCESS(f"기한 초과 {qs.count()}건 확인"))

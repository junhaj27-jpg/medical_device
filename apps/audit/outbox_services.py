from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import AuditExportOutbox


def audit_export_payload(log):
    return {"id":log.pk,"action":log.action,"model_name":log.model_name,"object_id":log.object_id,"request_id":str(log.request_id),"user_id":log.user_id_snapshot,"user_role":log.user_role,"reason":log.reason,"before":log.before_data,"after":log.after_data,"changed_fields":log.changed_fields,"created_at":log.created_at.isoformat(),"previous_hash":log.previous_hash,"current_hash":log.current_hash,"key_id":log.key_id,"algorithm":log.hash_algorithm,"schema_version":log.schema_version}


@transaction.atomic
def claim_outbox(now=None):
    now=now or timezone.now(); query=AuditExportOutbox.objects.filter(status__in=["PENDING","RETRY"],next_retry_at__lte=now)|AuditExportOutbox.objects.filter(status__in=["PENDING","RETRY"],next_retry_at__isnull=True)
    event=query.select_for_update().order_by("id").first()
    if not event: return None
    event.status=AuditExportOutbox.Status.PROCESSING; event.attempts+=1; event.save(update_fields=["status","attempts","updated_at"]); return event.pk


def process_one_outbox(exporter,now=None):
    now=now or timezone.now(); event_id=claim_outbox(now)
    if not event_id: return None
    event=AuditExportOutbox.objects.select_related("audit_log").get(pk=event_id)
    try:
        exporter.export(idempotency_key=event.idempotency_key,payload=audit_export_payload(event.audit_log))
    except (OSError,RuntimeError,TimeoutError,ValueError):
        if event.attempts>=settings.AUDIT_EXPORT_MAX_ATTEMPTS: event.status=AuditExportOutbox.Status.FAILED; event.next_retry_at=None
        else: event.status=AuditExportOutbox.Status.RETRY; event.next_retry_at=now+timezone.timedelta(seconds=settings.AUDIT_EXPORT_BACKOFF_SECONDS*(2**(event.attempts-1)))
        event.last_error_code="EXPORT_FAILED"; event.save(update_fields=["status","next_retry_at","last_error_code","updated_at"]); return event
    event.status=AuditExportOutbox.Status.SENT; event.sent_at=now; event.next_retry_at=None; event.last_error_code=""; event.save(update_fields=["status","sent_at","next_retry_at","last_error_code","updated_at"]); return event


def process_outbox_batch(exporter,limit=100):
    results=[]
    for _ in range(limit):
        event=process_one_outbox(exporter)
        if not event: break
        results.append(event)
    return results

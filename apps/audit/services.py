import hashlib
import hmac
import json
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms.models import model_to_dict
from django.utils import timezone

from .key_providers import get_key_provider
from .models import AuditChainState, AuditExportOutbox, AuditLog

SENSITIVE_KEYS = {
    "password", "token", "session", "api_key", "secret", "authorization",
    "phone", "address", "patient_name", "resident_number",
}
SCHEMA_VERSION = 2


def sanitize(value):
    if isinstance(value, dict):
        return {
            str(k): ("[REDACTED]" if any(s in str(k).lower() for s in SENSITIVE_KEYS) else sanitize(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize(v) for v in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "pk"):
        return value.pk
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def snapshot(instance, fields=None):
    data = model_to_dict(instance, fields=fields)
    return sanitize(data)


def _payload(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _digest(data,key): return hmac.new(key,_payload(data),hashlib.sha256).hexdigest()


@transaction.atomic
def record_audit(*, user, action, target, before=None, after=None, reason="", request=None, require_reason=False):
    if require_reason and not reason.strip():
        raise ValidationError("변경 사유가 필요합니다.")
    before = sanitize(before or {})
    after = sanitize(after if after is not None else snapshot(target))
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    chain, _ = AuditChainState.objects.get_or_create(name="default")
    chain = AuditChainState.objects.select_for_update().get(pk=chain.pk)
    request_id = getattr(request, "request_id", None) or uuid.uuid4()
    created_at = timezone.now()
    base = {
        "action": action, "model_name": target.__class__.__name__, "object_id": str(target.pk or ""),
        "before_data": before, "after_data": after, "changed_fields": changed,
        "request_id": str(request_id), "user_id_snapshot": str(user.pk) if user else "",
        "user_role": getattr(user, "role", ""), "reason": reason,
        "previous_hash": chain.current_hash, "created_at": created_at.isoformat(),
        "schema_version": SCHEMA_VERSION,
    }
    key=get_key_provider().active(); base["key_id"]=key.key_id; current_hash=_digest(base,key.value)
    log = AuditLog.objects.create(
        user=user, user_id_snapshot=base["user_id_snapshot"], user_role=base["user_role"], action=action,
        model_name=base["model_name"], object_id=base["object_id"], object_repr=str(target)[:255],
        before_data=before, after_data=after, changed_fields=changed, request_id=request_id,
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
        user_agent=request.headers.get("User-Agent", "")[:500] if request else "", reason=reason,
        previous_hash=chain.current_hash, current_hash=current_hash, key_id=key.key_id, hash_algorithm="HMAC-SHA256",
        schema_version=SCHEMA_VERSION,
        retention_expires_at=created_at + timedelta(days=settings.AUDIT_RETENTION_DAYS),
        created_at=created_at,
    )
    chain.current_hash=current_hash; chain.save(update_fields=["current_hash","updated_at"])
    AuditExportOutbox.objects.create(audit_log=log)
    return log


def verify_audit_chain_detailed():
    previous = ""
    results = []
    provider=get_key_provider()
    for log in AuditLog.objects.order_by("id"):
        base = {
            "action": log.action, "model_name": log.model_name, "object_id": log.object_id,
            "before_data": log.before_data, "after_data": log.after_data, "changed_fields": log.changed_fields,
            "request_id": str(log.request_id), "user_id_snapshot": log.user_id_snapshot,
            "user_role": log.user_role, "reason": log.reason, "previous_hash": log.previous_hash,
            "created_at": log.created_at.isoformat(), "schema_version": log.schema_version,
        }
        if log.schema_version>=2: base["key_id"]=log.key_id
        # Old records created before the hash-chain migration are explicitly outside the chain.
        if not log.current_hash:
            continue
        key=provider.get(log.key_id)
        if not key: status="KEY_UNAVAILABLE"
        elif log.previous_hash!=previous or not hmac.compare_digest(log.current_hash,_digest(base,key.value)): status="INVALID"
        else: status="VALID"
        results.append({"id":log.pk,"key_id":log.key_id,"status":status})
        previous = log.current_hash
    return results


def verify_audit_chain(): return [result["id"] for result in verify_audit_chain_detailed() if result["status"]!="VALID"]


def record_deletion_request(*,target,user,reason,request=None):
    return record_audit(user=user,action="DELETE_REQUEST",target=target,before=snapshot(target),after={"deletion_requested":True},reason=reason,request=request,require_reason=True)

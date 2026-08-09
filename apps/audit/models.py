from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); user_id_snapshot=models.CharField(max_length=100,blank=True); user_role=models.CharField(max_length=30,blank=True); action=models.CharField(max_length=50); model_name=models.CharField(max_length=100); object_id=models.CharField(max_length=100,blank=True); object_repr=models.CharField(max_length=255,blank=True); before_data=models.JSONField(default=dict,blank=True); after_data=models.JSONField(default=dict,blank=True); changed_fields=models.JSONField(default=list,blank=True); request_id=models.UUIDField(null=True,blank=True,db_index=True); ip_address=models.GenericIPAddressField(null=True,blank=True); user_agent=models.CharField(max_length=500,blank=True); reason=models.TextField(blank=True); previous_hash=models.CharField(max_length=64,blank=True); current_hash=models.CharField(max_length=64,blank=True,db_index=True); key_id=models.CharField(max_length=100,default="legacy"); hash_algorithm=models.CharField(max_length=20,default="HMAC-SHA256"); schema_version=models.PositiveSmallIntegerField(default=1); retention_expires_at=models.DateTimeField(null=True,blank=True); legal_hold=models.BooleanField(default=False); disposition_status=models.CharField(max_length=20,default="ACTIVE"); destroyed_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(default=timezone.now,editable=False)
    class Meta: ordering=["-created_at"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("감사 로그는 수정할 수 없습니다.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("감사 로그는 삭제할 수 없습니다.")


class AuditChainState(models.Model):
    name=models.CharField(max_length=30,unique=True,default="default"); current_hash=models.CharField(max_length=64,blank=True); updated_at=models.DateTimeField(auto_now=True)


class AuditExportOutbox(models.Model):
    class Status(models.TextChoices): PENDING="PENDING","대기"; PROCESSING="PROCESSING","처리 중"; RETRY="RETRY","재시도"; SENT="SENT","완료"; FAILED="FAILED","실패"
    audit_log=models.OneToOneField(AuditLog,on_delete=models.PROTECT,related_name="export_outbox"); idempotency_key=models.UUIDField(default=__import__("uuid").uuid4,unique=True,editable=False); status=models.CharField(max_length=20,choices=Status.choices,default=Status.PENDING); attempts=models.PositiveSmallIntegerField(default=0); next_retry_at=models.DateTimeField(null=True,blank=True); last_error_code=models.CharField(max_length=50,blank=True); sent_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)

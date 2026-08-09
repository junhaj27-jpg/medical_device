from django.conf import settings
from django.db import models


class Approval(models.Model):
    adverse_event=models.ForeignKey("adverse_events.AdverseEvent",on_delete=models.CASCADE,related_name="approvals"); requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="requested_approvals"); approver=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="assigned_approvals"); approval_type=models.CharField(max_length=30,default="FINAL"); decision=models.CharField(max_length=20,default="PENDING"); comment=models.TextField(blank=True); requested_at=models.DateTimeField(auto_now_add=True); decided_at=models.DateTimeField(null=True,blank=True)


class ElectronicSignature(models.Model):
    signer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="electronic_signatures"); signer_display_name=models.CharField(max_length=200); signer_role=models.CharField(max_length=30); meaning=models.CharField(max_length=100); reason=models.TextField(); target_model=models.CharField(max_length=100); target_id=models.CharField(max_length=100); target_version=models.PositiveIntegerField(default=1); canonical_data=models.JSONField(); data_hash=models.CharField(max_length=64); previous_hash=models.CharField(max_length=64,blank=True); current_hash=models.CharField(max_length=64,unique=True); hash_algorithm=models.CharField(max_length=20,default="HMAC-SHA256"); schema_version=models.PositiveSmallIntegerField(default=1); signed_at=models.DateTimeField()

    def save(self,*args,**kwargs):
        if self.pk: raise RuntimeError("전자서명은 수정할 수 없습니다.")
        super().save(*args,**kwargs)
    def delete(self,*args,**kwargs): raise RuntimeError("전자서명은 삭제할 수 없습니다.")


class SignatureRevocation(models.Model):
    signature=models.OneToOneField(ElectronicSignature,on_delete=models.PROTECT,related_name="revocation"); revoked_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT); reason=models.TextField(); revoked_at=models.DateTimeField(auto_now_add=True)

    def save(self,*args,**kwargs):
        if self.pk: raise RuntimeError("서명 무효화 기록은 수정할 수 없습니다.")
        super().save(*args,**kwargs)
    def delete(self,*args,**kwargs): raise RuntimeError("서명 무효화 기록은 삭제할 수 없습니다.")

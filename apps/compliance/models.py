from django.conf import settings
from django.db import models


class AnnualSequence(models.Model):
    document_type = models.CharField(max_length=20)
    year = models.PositiveSmallIntegerField()
    value = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document_type", "year"], name="unique_document_sequence_year"
            )
        ]


class RetentionPolicy(models.Model):
    record_type=models.CharField(max_length=100); version=models.PositiveIntegerField(); effective_from=models.DateField(); retention_days=models.PositiveIntegerField(); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=["record_type","version"],name="unique_retention_policy_version")]
    def save(self,*args,**kwargs):
        if self.pk: raise RuntimeError("보존정책 버전은 수정할 수 없습니다.")
        super().save(*args,**kwargs)
    def delete(self,*args,**kwargs): raise RuntimeError("보존정책 이력은 삭제할 수 없습니다.")


class LegalHold(models.Model):
    class Status(models.TextChoices): REQUESTED="REQUESTED","요청"; APPROVED="APPROVED","승인"; REJECTED="REJECTED","반려"; RELEASED="RELEASED","해제"
    target_model=models.CharField(max_length=100); target_id=models.CharField(max_length=100); requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="requested_legal_holds"); request_reason=models.TextField(); requested_at=models.DateTimeField(auto_now_add=True); approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True,related_name="approved_legal_holds"); approved_at=models.DateTimeField(null=True,blank=True); decision_reason=models.TextField(blank=True); status=models.CharField(max_length=20,choices=Status.choices,default=Status.REQUESTED); released_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True,related_name="released_legal_holds"); released_at=models.DateTimeField(null=True,blank=True)


class DestructionRequest(models.Model):
    class Status(models.TextChoices): REQUESTED="REQUESTED","요청"; APPROVED="APPROVED","승인"; REJECTED="REJECTED","반려"; EXECUTED="EXECUTED","파기 완료"
    target_model=models.CharField(max_length=100); target_id=models.CharField(max_length=100); requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="requested_destructions"); reason=models.TextField(); requested_at=models.DateTimeField(auto_now_add=True); approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True,related_name="approved_destructions"); approved_at=models.DateTimeField(null=True,blank=True); decision_reason=models.TextField(blank=True); status=models.CharField(max_length=20,choices=Status.choices,default=Status.REQUESTED); executed_at=models.DateTimeField(null=True,blank=True); evidence=models.JSONField(default=dict,blank=True)

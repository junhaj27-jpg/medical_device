from django.conf import settings
from django.db import models


class Investigation(models.Model):
    class ApprovalStatus(models.TextChoices): DRAFT="DRAFT","초안"; REVIEW_PENDING="REVIEW_PENDING","검토 대기"; APPROVED="APPROVED","승인"; REJECTED="REJECTED","반려"; NEEDS_REAPPROVAL="NEEDS_REAPPROVAL","재승인 필요"
    adverse_event=models.OneToOneField("adverse_events.AdverseEvent",on_delete=models.CASCADE,related_name="investigation"); investigator=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT); investigation_summary=models.TextField(); root_cause=models.TextField(); investigation_method=models.TextField(); evidence=models.TextField(blank=True); started_at=models.DateTimeField(); completed_at=models.DateTimeField(null=True,blank=True); status=models.CharField(max_length=30,default="IN_PROGRESS"); approval_status=models.CharField(max_length=30,choices=ApprovalStatus.choices,default=ApprovalStatus.DRAFT); approval_version=models.PositiveIntegerField(default=1); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)

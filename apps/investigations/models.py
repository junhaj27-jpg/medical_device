from django.conf import settings
from django.db import models


class Investigation(models.Model):
    adverse_event=models.OneToOneField("adverse_events.AdverseEvent",on_delete=models.CASCADE,related_name="investigation"); investigator=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT); investigation_summary=models.TextField(); root_cause=models.TextField(); investigation_method=models.TextField(); evidence=models.TextField(blank=True); started_at=models.DateTimeField(); completed_at=models.DateTimeField(null=True,blank=True); status=models.CharField(max_length=30,default="IN_PROGRESS"); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)

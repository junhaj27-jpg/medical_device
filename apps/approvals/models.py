from django.conf import settings
from django.db import models
class Approval(models.Model):
    adverse_event=models.ForeignKey("adverse_events.AdverseEvent",on_delete=models.CASCADE,related_name="approvals"); requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="requested_approvals"); approver=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="assigned_approvals"); approval_type=models.CharField(max_length=30,default="FINAL"); decision=models.CharField(max_length=20,default="PENDING"); comment=models.TextField(blank=True); requested_at=models.DateTimeField(auto_now_add=True); decided_at=models.DateTimeField(null=True,blank=True)

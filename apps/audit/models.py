from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); action=models.CharField(max_length=30); model_name=models.CharField(max_length=100); object_id=models.CharField(max_length=100,blank=True); object_repr=models.CharField(max_length=255,blank=True); before_data=models.JSONField(default=dict,blank=True); after_data=models.JSONField(default=dict,blank=True); ip_address=models.GenericIPAddressField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-created_at"]

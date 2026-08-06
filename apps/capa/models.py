from django.conf import settings
from django.db import models,transaction
from django.utils import timezone
class CAPA(models.Model):
    adverse_event=models.ForeignKey("adverse_events.AdverseEvent",on_delete=models.CASCADE,related_name="capas"); capa_number=models.CharField(max_length=22,unique=True,blank=True); capa_type=models.CharField(max_length=30); issue_description=models.TextField(); corrective_action=models.TextField(); preventive_action=models.TextField(); owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT); planned_completion_date=models.DateField(); actual_completion_date=models.DateField(null=True,blank=True); effectiveness_review=models.TextField(blank=True); effectiveness_result=models.CharField(max_length=40,blank=True); status=models.CharField(max_length=30,default="OPEN"); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    def save(self,*args,**kwargs):
        if not self.capa_number:
            year=timezone.localdate().year
            with transaction.atomic():
                last=CAPA.objects.select_for_update().filter(capa_number__startswith=f"CAPA-{year}-").order_by("capa_number").last(); seq=int(last.capa_number[-6:])+1 if last else 1; self.capa_number=f"CAPA-{year}-{seq:06d}"
        super().save(*args,**kwargs)
    @property
    def is_overdue(self): return self.status!="COMPLETED" and self.planned_completion_date<timezone.localdate()

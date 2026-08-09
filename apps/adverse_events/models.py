import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from .file_security import PrivateMediaStorage


def validate_attachment(value):
    from .file_security import validate_file_content

    validate_file_content(value)
class AdverseEvent(models.Model):
    class Severity(models.TextChoices): LOW="LOW","낮음"; MEDIUM="MEDIUM","보통"; HIGH="HIGH","높음"; CRITICAL="CRITICAL","치명적"
    class Reportability(models.TextChoices): UNDETERMINED="UNDETERMINED","미결정"; NOT_REPORTABLE="NOT_REPORTABLE","비보고"; REPORTABLE="REPORTABLE","보고"; URGENT_REPORTABLE="URGENT_REPORTABLE","긴급보고"
    class Status(models.TextChoices): RECEIVED="RECEIVED","접수"; UNDER_REVIEW="UNDER_REVIEW","검토"; INVESTIGATING="INVESTIGATING","조사"; CAPA_IN_PROGRESS="CAPA_IN_PROGRESS","CAPA"; APPROVAL_PENDING="APPROVAL_PENDING","승인대기"; REPORTING="REPORTING","보고"; CLOSED="CLOSED","종료"; REJECTED="REJECTED","반려"; ON_HOLD="ON_HOLD","보류"
    event_number=models.CharField(max_length=20,unique=True,blank=True); title=models.CharField(max_length=200); description=models.TextField(); medical_device=models.ForeignKey("devices.MedicalDevice",on_delete=models.PROTECT,related_name="events"); device_lot=models.ForeignKey("devices.DeviceLot",on_delete=models.PROTECT,related_name="events"); reporter=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="reported_events"); assigned_to=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="assigned_events"); occurred_at=models.DateTimeField(); reported_at=models.DateTimeField(default=timezone.now); event_location=models.CharField(max_length=150); patient_age_group=models.CharField(max_length=30,blank=True); patient_gender=models.CharField(max_length=20,blank=True); severity=models.CharField(max_length=10,choices=Severity.choices); reportability=models.CharField(max_length=20,choices=Reportability.choices,default=Reportability.UNDETERMINED); event_type=models.CharField(max_length=80); status=models.CharField(max_length=30,choices=Status.choices,default=Status.RECEIVED); due_date=models.DateField(null=True,blank=True); is_overdue=models.BooleanField(default=False); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    def save(self,*args,**kwargs):
        if not self.event_number:
            from apps.compliance.services import next_management_number

            self.event_number=next_management_number("ADVERSE_EVENT")
        self.is_overdue=bool(self.due_date and self.due_date<timezone.localdate() and self.status!=self.Status.CLOSED); super().save(*args,**kwargs)
    @property
    def deadline_label(self):
        if not self.due_date:return "미설정"
        d=(self.due_date-timezone.localdate()).days
        return "기한 초과" if d<0 else "오늘 마감" if d==0 else "3일 이내" if d<=3 else "7일 이내" if d<=7 else "정상"
    def __str__(self):return self.event_number
class PatientAnonymousInfo(models.Model):
    adverse_event=models.OneToOneField(AdverseEvent,on_delete=models.CASCADE,related_name="patient_info"); anonymous_code=models.CharField(max_length=50); age_group=models.CharField(max_length=30); gender=models.CharField(max_length=20); relevant_history=models.TextField(blank=True); outcome=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True)
class Attachment(models.Model):
    class ScanStatus(models.TextChoices):
        QUARANTINED="QUARANTINED","격리"; CLEAN="CLEAN","정상"; INFECTED="INFECTED","감염"; SCAN_FAILED="SCAN_FAILED","검사 실패"
    adverse_event=models.ForeignKey(AdverseEvent,on_delete=models.CASCADE,related_name="attachments"); uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT); original_name=models.CharField(max_length=255); storage_name=models.CharField(max_length=255,default=uuid.uuid4); file=models.FileField(upload_to="quarantine/%Y/%m/",storage=PrivateMediaStorage(),validators=[validate_attachment]); file_type=models.CharField(max_length=20); detected_mime=models.CharField(max_length=100,blank=True); sha256=models.CharField(max_length=64,blank=True); size=models.PositiveBigIntegerField(default=0); scan_status=models.CharField(max_length=20,choices=ScanStatus.choices,default=ScanStatus.QUARANTINED); scan_engine=models.CharField(max_length=100,blank=True); scan_attempts=models.PositiveSmallIntegerField(default=0); scan_next_retry_at=models.DateTimeField(null=True,blank=True); scan_error_code=models.CharField(max_length=50,blank=True); scanned_at=models.DateTimeField(null=True,blank=True); description=models.CharField(max_length=255,blank=True); retention_expires_at=models.DateTimeField(null=True,blank=True); legal_hold=models.BooleanField(default=False); deletion_scheduled_at=models.DateTimeField(null=True,blank=True); is_deleted=models.BooleanField(default=False); destroyed_at=models.DateTimeField(null=True,blank=True); uploaded_at=models.DateTimeField(auto_now_add=True)

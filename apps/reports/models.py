from django.conf import settings
from django.db import models
from django.utils import timezone


class RegulatoryReport(models.Model):
    class Type(models.TextChoices):
        INITIAL = "INITIAL", "최초"
        FOLLOW_UP = "FOLLOW_UP", "추가"
        FINAL = "FINAL", "최종"
        INTERNAL = "INTERNAL", "내부"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "초안"
        REVIEW_PENDING = "REVIEW_PENDING", "검토 대기"
        APPROVED = "APPROVED", "승인"
        GENERATED = "GENERATED", "문서 생성"
        SUBMITTED = "SUBMITTED", "제출 완료"
        REJECTED = "REJECTED", "반려"

    adverse_event = models.ForeignKey("adverse_events.AdverseEvent", on_delete=models.CASCADE, related_name="reports")
    report_number = models.CharField(max_length=22, unique=True, blank=True)
    regulatory_authority = models.CharField(max_length=100)
    report_type = models.CharField(max_length=20, choices=Type.choices, default=Type.INITIAL)
    report_status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    title = models.CharField(max_length=200, default="")
    event_summary = models.TextField(default="")
    device_information = models.TextField(default="")
    patient_information = models.TextField(blank=True)
    investigation_summary = models.TextField(blank=True)
    root_cause_summary = models.TextField(blank=True)
    capa_summary = models.TextField(blank=True)
    conclusion = models.TextField(blank=True)
    submission_due_date = models.DateField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="submitted_reports")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_reports")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_reports")
    document_file = models.FileField(upload_to="reports/", blank=True)
    document_version = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="created_reports")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.report_number:
            from apps.compliance.services import next_management_number

            self.report_number = next_management_number("REGULATORY_REPORT")
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return bool(self.submission_due_date and self.submission_due_date < timezone.localdate() and self.report_status != self.Status.SUBMITTED)

    def __str__(self):
        return self.report_number

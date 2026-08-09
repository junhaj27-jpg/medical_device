from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class CAPA(models.Model):
    class ApprovalStatus(models.TextChoices): DRAFT="DRAFT","초안"; REVIEW_PENDING="REVIEW_PENDING","검토 대기"; APPROVED="APPROVED","승인"; REJECTED="REJECTED","반려"; NEEDS_REAPPROVAL="NEEDS_REAPPROVAL","재승인 필요"
    class Type(models.TextChoices):
        CORRECTIVE = "CORRECTIVE", "시정조치"
        PREVENTIVE = "PREVENTIVE", "예방조치"
        CORRECTIVE_PREVENTIVE = "CORRECTIVE_PREVENTIVE", "시정·예방조치"

    class Effectiveness(models.TextChoices):
        NOT_REVIEWED = "NOT_REVIEWED", "미평가"
        EFFECTIVE = "EFFECTIVE", "효과적"
        PARTIALLY_EFFECTIVE = "PARTIALLY_EFFECTIVE", "부분 효과"
        INEFFECTIVE = "INEFFECTIVE", "효과 없음"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "초안"
        IN_PROGRESS = "IN_PROGRESS", "진행 중"
        REVIEW_PENDING = "REVIEW_PENDING", "검토 대기"
        COMPLETED = "COMPLETED", "완료"
        CLOSED = "CLOSED", "종료"
        CANCELLED = "CANCELLED", "취소"

    adverse_event = models.ForeignKey("adverse_events.AdverseEvent", on_delete=models.CASCADE, related_name="capas")
    capa_number = models.CharField(max_length=22, unique=True, blank=True)
    capa_type = models.CharField(max_length=30, choices=Type.choices, default=Type.CORRECTIVE_PREVENTIVE)
    issue_description = models.TextField()
    root_cause = models.TextField(default="")
    corrective_action = models.TextField(blank=True)
    preventive_action = models.TextField(blank=True)
    action_plan = models.TextField(default="")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_capas")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_capas")
    planned_start_date = models.DateField(default=timezone.localdate)
    planned_completion_date = models.DateField()
    actual_start_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField(null=True, blank=True)
    effectiveness_review = models.TextField(blank=True)
    effectiveness_result = models.CharField(max_length=30, choices=Effectiveness.choices, default=Effectiveness.NOT_REVIEWED)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    completion_percentage = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="created_capas")
    approval_status=models.CharField(max_length=30,choices=ApprovalStatus.choices,default=ApprovalStatus.DRAFT); approval_version=models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.capa_number:
            from apps.compliance.services import next_management_number

            self.capa_number = next_management_number("CAPA")
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return self.status not in {self.Status.COMPLETED, self.Status.CLOSED, self.Status.CANCELLED} and self.planned_completion_date < timezone.localdate()

    def __str__(self):
        return self.capa_number

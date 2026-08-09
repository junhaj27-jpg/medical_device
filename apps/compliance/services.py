from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import AnnualSequence

MAX_SEQUENCE_RETRIES = 5
FORMATS = {
    "ADVERSE_EVENT": ("AE", 6),
    "CAPA": ("CAPA", 6),
    "REGULATORY_REPORT": ("RPT", 6),
}


class SequenceGenerationError(ValidationError):
    pass


def next_management_number(document_type, *, year=None):
    if document_type not in FORMATS:
        raise SequenceGenerationError("지원하지 않는 관리번호 유형입니다.")
    year = year or timezone.localdate().year
    prefix, width = FORMATS[document_type]

    for attempt in range(MAX_SEQUENCE_RETRIES):
        try:
            # IntegrityError가 발생한 atomic 블록은 폐기하고 다음 반복에서 새 블록을 연다.
            with transaction.atomic():
                try:
                    sequence = AnnualSequence.objects.select_for_update().get(
                        document_type=document_type, year=year
                    )
                    AnnualSequence.objects.filter(pk=sequence.pk).update(value=F("value") + 1)
                    sequence.refresh_from_db(fields=["value"])
                except AnnualSequence.DoesNotExist:
                    sequence = AnnualSequence.objects.create(
                        document_type=document_type, year=year, value=1
                    )
                return f"{prefix}-{year}-{sequence.value:0{width}d}"
        except IntegrityError as exc:
            if attempt == MAX_SEQUENCE_RETRIES - 1:
                raise SequenceGenerationError(
                    f"{document_type} 관리번호를 {MAX_SEQUENCE_RETRIES}회 시도 후 생성하지 못했습니다."
                ) from exc

    raise SequenceGenerationError("관리번호 생성에 실패했습니다.")

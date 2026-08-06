from rest_framework import serializers
from .models import AdverseEvent
class AdverseEventSerializer(serializers.ModelSerializer):
    deadline_label=serializers.ReadOnlyField()
    class Meta: model=AdverseEvent; fields="__all__"; read_only_fields=["event_number","reporter","is_overdue"]

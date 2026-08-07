from django import forms

from .models import AdverseEvent


class AdverseEventForm(forms.ModelForm):
    anonymous_code=forms.CharField(max_length=50); anonymous_history=forms.CharField(widget=forms.Textarea,required=False); patient_outcome=forms.CharField(widget=forms.Textarea,required=False)
    class Meta:
        model=AdverseEvent; fields=["title","description","medical_device","device_lot","occurred_at","event_location","patient_age_group","patient_gender","event_type","severity","due_date"]
        widgets={"occurred_at":forms.DateTimeInput(attrs={"type":"datetime-local"}),"due_date":forms.DateInput(attrs={"type":"date"})}
    def clean(self):
        data=super().clean(); lot=data.get("device_lot"); device=data.get("medical_device")
        if lot and device and lot.medical_device_id!=device.id: self.add_error("device_lot","선택 제품의 LOT가 아닙니다.")
        return data

from django import forms
from .models import RegulatoryReport
class ReportForm(forms.ModelForm):
    class Meta:
        model=RegulatoryReport
        fields=["adverse_event","regulatory_authority","report_type","title","event_summary","device_information","patient_information","investigation_summary","root_cause_summary","capa_summary","conclusion","submission_due_date"]
        widgets={"submission_due_date":forms.DateInput(attrs={"type":"date"})}

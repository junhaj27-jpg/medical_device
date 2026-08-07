from django import forms

from .models import CAPA


class CAPAForm(forms.ModelForm):
    class Meta:
        model=CAPA
        fields=["adverse_event","capa_type","issue_description","root_cause","corrective_action","preventive_action","action_plan","owner","reviewer","planned_start_date","planned_completion_date","actual_start_date","actual_completion_date","completion_percentage","effectiveness_review","effectiveness_result"]
        widgets={name:forms.DateInput(attrs={"type":"date"}) for name in ["planned_start_date","planned_completion_date","actual_start_date","actual_completion_date"]}
    def clean(self):
        d=super().clean()
        if d.get("planned_start_date") and d.get("planned_completion_date") and d["planned_completion_date"]<d["planned_start_date"]: self.add_error("planned_completion_date","계획 완료일을 확인하세요.")
        if d.get("actual_start_date") and d.get("actual_completion_date") and d["actual_completion_date"]<d["actual_start_date"]: self.add_error("actual_completion_date","실제 완료일을 확인하세요.")
        return d

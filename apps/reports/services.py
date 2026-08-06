from pathlib import Path
from django.conf import settings
from docx import Document
def generate_event_report(event,author):
    doc=Document(); doc.add_heading("의료기기 이상사례 보고서",0)
    rows=[("보고서 번호",f"RPT-{event.event_number}"),("이상사례 번호",event.event_number),("제품 정보",str(event.medical_device)),("LOT / 시리얼",str(event.device_lot)),("발생일",str(event.occurred_at)),("접수일",str(event.reported_at)),("사건 개요",event.description),("심각도",event.severity),("보고 대상",event.reportability)]
    if hasattr(event,"patient_info"): rows += [("익명 환자",f"{event.patient_info.anonymous_code} / {event.patient_info.age_group} / {event.patient_info.gender}")]
    if hasattr(event,"investigation"): rows += [("조사 내용",event.investigation.investigation_summary),("근본 원인",event.investigation.root_cause)]
    rows += [("CAPA","; ".join(c.corrective_action for c in event.capas.all())),("승인 정보","; ".join(f"{a.approver}:{a.decision}" for a in event.approvals.all())),("작성자",author.get_username())]
    table=doc.add_table(rows=0,cols=2)
    for k,v in rows: cells=table.add_row().cells; cells[0].text=str(k); cells[1].text=str(v)
    target=Path(settings.MEDIA_ROOT)/"reports"/f"{event.event_number}_report.docx"; target.parent.mkdir(parents=True,exist_ok=True); doc.save(target); return target

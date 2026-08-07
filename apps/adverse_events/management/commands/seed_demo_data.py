import os
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.adverse_events.models import AdverseEvent, PatientAnonymousInfo
from apps.approvals.models import Approval
from apps.capa.models import CAPA
from apps.devices.models import DeviceLot, MedicalDevice
from apps.investigations.models import Investigation
from apps.reports.models import RegulatoryReport
from apps.reports.services import populate_report_fields


class Command(BaseCommand):
    help="포트폴리오 데모 데이터를 멱등하게 생성합니다."
    def handle(self,*args,**opts):
        users={}; today=timezone.localdate()
        demo_accounts = [
            ("admin", "DEMO_ADMIN_PASSWORD", "ADMIN"),
            ("rauser", "DEMO_RA_PASSWORD", "RA_QA"),
            ("staff", "DEMO_STAFF_PASSWORD", "STAFF"),
        ]
        missing = [env_name for _, env_name, _ in demo_accounts if not os.getenv(env_name)]
        if missing:
            raise CommandError(
                "데모 계정 생성에 필요한 환경변수가 없습니다: " + ", ".join(missing)
            )
        for name,env_name,role in demo_accounts:
            u,created=User.objects.get_or_create(username=name,defaults={"role":role,"email":f"{name}@example.test"})
            u.role=role; u.is_staff=role=="ADMIN"; u.is_superuser=role=="ADMIN"
            if created:
                u.set_password(os.environ[env_name])
            u.save(); users[name]=u
        devices=[]; lots=[]
        for i in range(5):
            d,_=MedicalDevice.objects.get_or_create(device_code=f"MD-{i+1:03d}",defaults={"product_name":f"환자감시장치 {i+1}","model_name":f"PM-{100+i}","manufacturer":"MDSafe Medical","product_category":"모니터링","approval_number":f"허가-2026-{i+1:03d}","risk_class":"2등급"}); devices.append(d)
            for j in range(2):
                lot,_=DeviceLot.objects.get_or_create(medical_device=d,lot_number=f"LOT-{i+1:02d}-{j+1:02d}",serial_number=f"SN{i+1:02d}{j+1:03d}",defaults={"manufacture_date":today-timedelta(days=180),"expiration_date":today+timedelta(days=900),"distribution_date":today-timedelta(days=90),"distribution_location":"서울 의료기관"}); lots.append(lot)
        events=[]; event_statuses=["RECEIVED","UNDER_REVIEW","INVESTIGATING","CAPA_IN_PROGRESS","APPROVAL_PENDING"]
        for i in range(15):
            defaults={"description":"사용 중 표시 오류가 관찰되어 원인 분석이 필요합니다.","medical_device":devices[i%5],"device_lot":lots[i%10],"reporter":users["staff"],"assigned_to":users["rauser"],"occurred_at":timezone.now()-timedelta(days=i+1),"event_location":"서울 의료기관","patient_age_group":"성인","patient_gender":"미상","severity":["LOW","MEDIUM","HIGH","CRITICAL"][i%4],"event_type":"기기 오작동","status":event_statuses[i%5],"due_date":today-timedelta(days=2-i) if i<2 else today+timedelta(days=i)}
            e,_=AdverseEvent.objects.get_or_create(title=f"샘플 이상사례 {i+1}",defaults=defaults); events.append(e); PatientAnonymousInfo.objects.get_or_create(adverse_event=e,defaults={"anonymous_code":f"P-{i+1:04d}","age_group":"성인","gender":"미상","outcome":"회복"})
        for e in events[:8]: Investigation.objects.get_or_create(adverse_event=e,defaults={"investigator":users["rauser"],"investigation_summary":"설계·제조·사용 환경 검토 완료","root_cause":"연결부 접촉 불량","investigation_method":"기록 검토 및 재현 시험","started_at":timezone.now()-timedelta(days=5),"completed_at":timezone.now()})
        capa_states=["IN_PROGRESS"]*3+["IN_PROGRESS"]*2+["COMPLETED"]*2+["CLOSED"]
        for i,e in enumerate(events[:8]):
            defaults={"capa_type":"CORRECTIVE_PREVENTIVE","root_cause":"접촉 불량","corrective_action":"해당 LOT 전수 검사","preventive_action":"수입검사 기준 강화","action_plan":"검사, 개선, 효과성 검토 순으로 수행","owner":users["rauser"],"reviewer":users["admin"],"planned_start_date":today-timedelta(days=10),"planned_completion_date":today-timedelta(days=2) if i in (3,4) else today+timedelta(days=10+i),"status":capa_states[i],"completion_percentage":100 if i>=5 else 60,"actual_completion_date":today if i>=5 else None,"effectiveness_review":"재발 없음 확인" if i==7 else "","effectiveness_result":"EFFECTIVE" if i==7 else "NOT_REVIEWED","created_by":users["rauser"]}
            CAPA.objects.update_or_create(adverse_event=e,issue_description=f"샘플 CAPA 문제 {i+1}",defaults=defaults)
        report_states=["DRAFT","DRAFT","REVIEW_PENDING","REVIEW_PENDING","APPROVED","SUBMITTED","SUBMITTED","DRAFT"]
        for i,e in enumerate(events[:8]):
            data=populate_report_fields(e); data.update({"regulatory_authority":"식품의약품안전처","report_type":"INITIAL","report_status":report_states[i],"submission_due_date":today-timedelta(days=1) if i==7 else today+timedelta(days=7+i),"created_by":users["rauser"],"submitted_by":users["rauser"] if report_states[i]=="SUBMITTED" else None,"submitted_at":timezone.now() if report_states[i]=="SUBMITTED" else None})
            RegulatoryReport.objects.update_or_create(adverse_event=e,report_type="INITIAL",defaults=data)
        for e in events[4:7]: Approval.objects.get_or_create(adverse_event=e,requested_by=users["rauser"],approver=users["admin"],defaults={"decision":"PENDING"})
        self.stdout.write(self.style.SUCCESS("데모 계정, CAPA 8건, 규제 보고서 8건 생성 완료"))

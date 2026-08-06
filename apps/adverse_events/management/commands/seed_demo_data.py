from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User
from apps.devices.models import MedicalDevice,DeviceLot
from apps.adverse_events.models import AdverseEvent,PatientAnonymousInfo
from apps.investigations.models import Investigation
from apps.capa.models import CAPA
from apps.approvals.models import Approval
class Command(BaseCommand):
    help="포트폴리오 데모 데이터를 멱등하게 생성합니다."
    def handle(self,*args,**opts):
        users={}
        for name,password,role in [("admin","Admin1234!","ADMIN"),("rauser","Rauser1234!","RA_QA"),("staff","Staff1234!","STAFF")]:
            u,_=User.objects.get_or_create(username=name,defaults={"role":role,"email":f"{name}@example.test"}); u.role=role; u.is_staff=role=="ADMIN"; u.is_superuser=role=="ADMIN"; u.set_password(password); u.save(); users[name]=u
        devices=[]; lots=[]; today=timezone.localdate()
        for i in range(5):
            d,_=MedicalDevice.objects.get_or_create(device_code=f"MD-{i+1:03d}",defaults={"product_name":f"환자감시장치 {i+1}","model_name":f"PM-{100+i}","manufacturer":"MDSafe Medical","product_category":"모니터링","approval_number":f"허가-2026-{i+1:03d}","risk_class":"2등급"}); devices.append(d)
            for j in range(2):
                lot,_=DeviceLot.objects.get_or_create(medical_device=d,lot_number=f"LOT-{i+1:02d}-{j+1:02d}",serial_number=f"SN{i+1:02d}{j+1:03d}",defaults={"manufacture_date":today-timedelta(days=180),"expiration_date":today+timedelta(days=900),"distribution_date":today-timedelta(days=90),"distribution_location":"서울 의료기관"}); lots.append(lot)
        statuses=["RECEIVED","UNDER_REVIEW","INVESTIGATING","CAPA_IN_PROGRESS","APPROVAL_PENDING"]
        events=[]
        for i in range(15):
            defaults={"title":f"샘플 이상사례 {i+1}","description":"사용 중 표시 오류가 관찰되어 원인 분석이 필요합니다.","medical_device":devices[i%5],"device_lot":lots[i%10],"reporter":users["staff"],"assigned_to":users["rauser"],"occurred_at":timezone.now()-timedelta(days=i+1),"event_location":"서울 의료기관","patient_age_group":"성인","patient_gender":"미상","severity":["LOW","MEDIUM","HIGH","CRITICAL"][i%4],"event_type":"기기 오작동","status":statuses[i%5],"due_date":today-timedelta(days=2-i) if i<2 else today+timedelta(days=i)}
            e,_=AdverseEvent.objects.get_or_create(title=defaults["title"],defaults=defaults); events.append(e); PatientAnonymousInfo.objects.get_or_create(adverse_event=e,defaults={"anonymous_code":f"P-{i+1:04d}","age_group":"성인","gender":"미상","outcome":"회복"})
        for i,e in enumerate(events[:5]):
            Investigation.objects.get_or_create(adverse_event=e,defaults={"investigator":users["rauser"],"investigation_summary":"설계·제조·사용 환경 검토 완료","root_cause":"연결부 접촉 불량","investigation_method":"기록 검토 및 재현 시험","started_at":timezone.now()-timedelta(days=5),"completed_at":timezone.now()})
            CAPA.objects.get_or_create(adverse_event=e,issue_description="접촉 신뢰성 개선 필요",defaults={"capa_type":"CORRECTIVE_PREVENTIVE","corrective_action":"해당 LOT 검사","preventive_action":"검사 기준 강화","owner":users["rauser"],"planned_completion_date":today+timedelta(days=30)})
        for e in events[4:7]: Approval.objects.get_or_create(adverse_event=e,requested_by=users["rauser"],approver=users["admin"],defaults={"decision":"PENDING"}); e.status="APPROVAL_PENDING"; e.save()
        self.stdout.write(self.style.SUCCESS("데모 계정 3개, 제품 5개, LOT 10개, 이상사례 15개 생성 완료"))

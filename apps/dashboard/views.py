import csv,json
from django.contrib.auth.decorators import login_required,user_passes_test
from django.db.models import Count
from django.http import HttpResponse,HttpResponseForbidden
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from apps.adverse_events.forms import AdverseEventForm
from apps.adverse_events.models import AdverseEvent,PatientAnonymousInfo
from apps.audit.models import AuditLog
from apps.capa.models import CAPA
from apps.devices.models import MedicalDevice
from apps.reports.models import RegulatoryReport
def scoped(user): return AdverseEvent.objects.filter(reporter=user) if user.role=="STAFF" else AdverseEvent.objects.all()
@login_required
def dashboard(request):
    qs=scoped(request.user); today=timezone.localdate(); stats={"total":qs.count(),"received":qs.filter(status="RECEIVED").count(),"investigating":qs.filter(status="INVESTIGATING").count(),"capa":qs.filter(status="CAPA_IN_PROGRESS").count(),"approval":qs.filter(status="APPROVAL_PENDING").count(),"soon":qs.filter(due_date__gte=today,due_date__lte=today+timezone.timedelta(days=7)).count(),"overdue":qs.filter(due_date__lt=today).exclude(status="CLOSED").count(),"closed":qs.filter(status="CLOSED").count()}
    severity=list(qs.values("severity").annotate(count=Count("id"))); status=list(qs.values("status").annotate(count=Count("id")))
    capas=CAPA.objects.all(); reports=RegulatoryReport.objects.all()
    stats.update({"capa_active":capas.filter(status="IN_PROGRESS").count(),"capa_overdue":sum(c.is_overdue for c in capas),"capa_review":capas.filter(status="REVIEW_PENDING").count(),"effect_pending":capas.filter(status="COMPLETED",effectiveness_result="NOT_REVIEWED").count(),"report_draft":reports.filter(report_status="DRAFT").count(),"report_review":reports.filter(report_status="REVIEW_PENDING").count(),"report_soon":reports.filter(submission_due_date__gte=today,submission_due_date__lte=today+timezone.timedelta(days=7)).exclude(report_status="SUBMITTED").count(),"report_overdue":sum(r.is_overdue for r in reports)})
    return render(request,"dashboard.html",{"stats":stats,"recent":qs.select_related("medical_device").order_by("-created_at")[:8],"severity_json":json.dumps(severity),"status_json":json.dumps(status),"capa_status_json":json.dumps(list(capas.values("status").annotate(count=Count("id")))),"report_status_json":json.dumps(list(reports.values("report_status").annotate(count=Count("id")))),"urgent_capas":[c for c in capas.order_by("planned_completion_date") if c.is_overdue][:5],"urgent_reports":[r for r in reports.order_by("submission_due_date") if r.is_overdue][:5]})
@login_required
def event_list(request):
    qs=scoped(request.user).select_related("medical_device","device_lot","assigned_to").order_by("-created_at")
    q=request.GET.get("q",""); status=request.GET.get("status",""); severity=request.GET.get("severity","")
    if q: qs=qs.filter(event_number__icontains=q)|qs.filter(title__icontains=q)|qs.filter(medical_device__product_name__icontains=q)
    if status: qs=qs.filter(status=status)
    if severity: qs=qs.filter(severity=severity)
    if request.GET.get("format")=="csv":
        res=HttpResponse(content_type="text/csv; charset=utf-8"); res["Content-Disposition"]='attachment; filename="events.csv"'; res.write("\ufeff"); w=csv.writer(res); w.writerow(["사건번호","제목","제품","심각도","상태","기한"]); [w.writerow([e.event_number,e.title,e.medical_device,e.severity,e.status,e.due_date]) for e in qs]; return res
    return render(request,"events/list.html",{"events":qs,"statuses":AdverseEvent.Status.choices,"severities":AdverseEvent.Severity.choices})
@login_required
def event_create(request):
    form=AdverseEventForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        event=form.save(commit=False); event.reporter=request.user; event.status="RECEIVED"; event.save(); PatientAnonymousInfo.objects.create(adverse_event=event,anonymous_code=form.cleaned_data["anonymous_code"],age_group=event.patient_age_group,gender=event.patient_gender,relevant_history=form.cleaned_data["anonymous_history"],outcome=form.cleaned_data["patient_outcome"]); AuditLog.objects.create(user=request.user,action="CREATE",model_name="AdverseEvent",object_id=str(event.pk),object_repr=event.event_number,after_data={"event_number":event.event_number,"title":event.title}); return redirect("event_detail",pk=event.pk)
    return render(request,"events/form.html",{"form":form})
@login_required
def event_detail(request,pk):
    event=get_object_or_404(scoped(request.user).select_related("medical_device","device_lot"),pk=pk); return render(request,"events/detail.html",{"event":event})
@login_required
def report_download(request,pk): return redirect("reports:create")
@login_required
def devices(request): return render(request,"devices.html",{"devices":MedicalDevice.objects.prefetch_related("lots")})
@login_required
def capas(request): return render(request,"capas.html",{"capas":CAPA.objects.select_related("adverse_event","owner")})
@user_passes_test(lambda u:u.is_authenticated and u.role=="ADMIN")
def audits(request): return render(request,"audits.html",{"logs":AuditLog.objects.select_related("user")[:200]})

import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.core.paginator import Paginator
from django.http import FileResponse,HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from apps.adverse_events.models import AdverseEvent
from .forms import ReportForm
from .models import RegulatoryReport
from .services import create_report_from_event,populate_report_fields,request_report_review,approve_report,generate_docx_report,mark_report_submitted,_audit
def _qs(user):
    qs=RegulatoryReport.objects.select_related("adverse_event","created_by","approved_by")
    return qs.filter(adverse_event__reporter=user) if user.role=="STAFF" else qs
@login_required
def report_list(request):
    qs=_qs(request.user).order_by("-created_at"); q=request.GET.get("q","")
    if q: qs=qs.filter(report_number__icontains=q)|qs.filter(adverse_event__event_number__icontains=q)|qs.filter(title__icontains=q)
    for f in ("report_type","report_status","regulatory_authority"):
        if request.GET.get(f): qs=qs.filter(**{f:request.GET[f]})
    if request.GET.get("overdue")=="1": qs=[r for r in qs if r.is_overdue]
    if request.GET.get("format")=="csv":
        res=HttpResponse(content_type="text/csv; charset=utf-8"); res["Content-Disposition"]='attachment; filename="reports.csv"'; res.write("\ufeff"); w=csv.writer(res); w.writerow(["보고서","이상사례","제목","기관","유형","상태","기한","버전"]); [w.writerow([r.report_number,r.adverse_event.event_number,r.title,r.regulatory_authority,r.report_type,r.report_status,r.submission_due_date,r.document_version]) for r in qs]; return res
    return render(request,"reports/list.html",{"page":Paginator(qs,15).get_page(request.GET.get("page")),"statuses":RegulatoryReport.Status.choices,"types":RegulatoryReport.Type.choices})
@login_required
def report_create(request):
    if request.user.role not in {"RA_QA","ADMIN"}: raise PermissionDenied
    initial={"adverse_event":request.GET.get("event")}
    if request.method=="GET" and request.GET.get("event"):
        event=get_object_or_404(AdverseEvent,pk=request.GET["event"]); initial.update(populate_report_fields(event))
    form=ReportForm(request.POST or None,initial=initial)
    if request.method=="POST" and form.is_valid():
        data=form.cleaned_data.copy(); event=data.pop("adverse_event"); report=create_report_from_event(event,request.user,**data); return redirect("reports:detail",pk=report.pk)
    return render(request,"reports/form.html",{"form":form,"mode":"작성"})
@login_required
def report_edit(request,pk):
    if request.user.role not in {"RA_QA","ADMIN"}: raise PermissionDenied
    report=get_object_or_404(_qs(request.user),pk=pk); form=ReportForm(request.POST or None,instance=report)
    if request.method=="POST" and form.is_valid(): form.save(); _audit(request.user,"REPORT_UPDATE",report,request=request); return redirect("reports:detail",pk=pk)
    return render(request,"reports/form.html",{"form":form,"mode":"수정","report":report})
@login_required
def report_detail(request,pk): return render(request,"reports/detail.html",{"report":get_object_or_404(_qs(request.user),pk=pk)})
@login_required
def report_action(request,pk,action):
    if request.method!="POST": raise PermissionDenied
    report=get_object_or_404(_qs(request.user),pk=pk)
    try:
        if action=="review":request_report_review(report,request.user)
        elif action=="approve":approve_report(report,request.user)
        elif action=="generate":generate_docx_report(report,request.user,request)
        elif action=="submit":mark_report_submitted(report,request.user,request)
    except (ValidationError,PermissionDenied) as e: messages.error(request,str(e))
    return redirect("reports:detail",pk=pk)
@login_required
def report_download(request,pk):
    report=get_object_or_404(_qs(request.user),pk=pk)
    if not report.document_file: raise ValidationError("생성된 문서가 없습니다.")
    _audit(request.user,"REPORT_DOWNLOAD",report,request=request); return FileResponse(report.document_file.open("rb"),as_attachment=True,filename=report.document_file.name.split("/")[-1])

import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from .forms import CAPAForm
from .models import CAPA
from .services import create_capa,update_capa,change_capa_status,reopen_capa

def _qs(user):
    qs=CAPA.objects.select_related("adverse_event","owner","reviewer","created_by")
    return qs.filter(adverse_event__reporter=user) if user.role=="STAFF" else qs
@login_required
def capa_list(request):
    qs=_qs(request.user).order_by("-created_at"); q=request.GET.get("q","")
    if q: qs=qs.filter(capa_number__icontains=q)|qs.filter(adverse_event__event_number__icontains=q)|qs.filter(adverse_event__title__icontains=q)
    for field in ("status","capa_type","effectiveness_result","owner"):
        if request.GET.get(field): qs=qs.filter(**{field:request.GET[field]})
    if request.GET.get("overdue")=="1": qs=[c for c in qs if c.is_overdue]
    if request.GET.get("format")=="csv":
        res=HttpResponse(content_type="text/csv; charset=utf-8"); res["Content-Disposition"]='attachment; filename="capas.csv"'; res.write("\ufeff"); w=csv.writer(res); w.writerow(["CAPA","이상사례","유형","담당자","완료일","진행률","효과성","상태"]); [w.writerow([c.capa_number,c.adverse_event.event_number,c.capa_type,c.owner,c.planned_completion_date,c.completion_percentage,c.effectiveness_result,c.status]) for c in qs]; return res
    return render(request,"capa/list.html",{"page":Paginator(qs,15).get_page(request.GET.get("page")),"statuses":CAPA.Status.choices,"types":CAPA.Type.choices,"effects":CAPA.Effectiveness.choices})
@login_required
def capa_create(request):
    if request.user.role not in {"RA_QA","ADMIN"}: raise PermissionDenied
    form=CAPAForm(request.POST or None,initial={"adverse_event":request.GET.get("event")})
    if request.method=="POST" and form.is_valid():
        try: capa=create_capa(request.user,**form.cleaned_data); messages.success(request,"CAPA가 생성되었습니다."); return redirect("capa:detail",pk=capa.pk)
        except ValidationError as e: form.add_error(None,e)
    return render(request,"capa/form.html",{"form":form,"mode":"등록"})
@login_required
def capa_edit(request,pk):
    if request.user.role not in {"RA_QA","ADMIN"}: raise PermissionDenied
    capa=get_object_or_404(_qs(request.user),pk=pk); form=CAPAForm(request.POST or None,instance=capa)
    if request.method=="POST" and form.is_valid(): update_capa(capa,request.user,**form.cleaned_data); return redirect("capa:detail",pk=pk)
    return render(request,"capa/form.html",{"form":form,"mode":"수정","capa":capa})
@login_required
def capa_detail(request,pk): return render(request,"capa/detail.html",{"capa":get_object_or_404(_qs(request.user),pk=pk),"statuses":CAPA.Status.choices})
@login_required
def capa_status(request,pk):
    if request.method!="POST": raise PermissionDenied
    capa=get_object_or_404(_qs(request.user),pk=pk)
    try:
        if request.POST.get("status")=="REOPEN": reopen_capa(capa,request.user,request)
        else: change_capa_status(capa,request.POST["status"],request.user,request)
        messages.success(request,"상태가 변경되었습니다.")
    except (ValidationError,PermissionDenied) as e: messages.error(request,str(e))
    return redirect("capa:detail",pk=pk)

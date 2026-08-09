from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from apps.approvals.services import approve_investigation, reject_signature_target, request_signature_review

from .models import Investigation


def _qs(user):
    qs=Investigation.objects.select_related("adverse_event","investigator")
    return qs.filter(adverse_event__reporter=user) if user.role=="STAFF" else qs

@login_required
def detail(request,pk): return render(request,"investigations/detail.html",{"investigation":get_object_or_404(_qs(request.user),pk=pk)})

@login_required
def approval(request,pk,action):
    if request.method!="POST": raise PermissionDenied
    investigation=get_object_or_404(_qs(request.user),pk=pk)
    try:
        if action=="review": request_signature_review(investigation,user=request.user,request=request)
        elif action=="approve": approve_investigation(investigation,user=request.user,password=request.POST.get("password"),reason=request.POST.get("reason",""),request=request)
        elif action=="reject": reject_signature_target(investigation,user=request.user,password=request.POST.get("password"),reason=request.POST.get("reason",""),request=request)
        else: raise ValidationError("알 수 없는 승인 작업입니다.")
        messages.success(request,"조사 전자서명 작업이 처리되었습니다.")
    except (PermissionDenied,ValidationError) as exc: messages.error(request,str(exc))
    return redirect("investigations:detail",pk=pk)

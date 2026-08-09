from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404

from .attachment_services import authorize_download
from .models import Attachment
from .storage_adapters import LocalPrivateStorageAdapter


@login_required
def download_attachment(request,pk):
    attachment=get_object_or_404(Attachment.objects.select_related("adverse_event"),pk=pk); authorize_download(attachment,request.user)
    if request.GET.get("signature") and not LocalPrivateStorageAdapter.verify_signed_request(attachment.file.name,expires=request.GET.get("expires","0"),subject_id=request.user.pk,signature=request.GET["signature"]): raise PermissionDenied("서명 URL이 만료되었거나 유효하지 않습니다.")
    return FileResponse(attachment.file.open("rb"),as_attachment=True,filename=attachment.original_name)

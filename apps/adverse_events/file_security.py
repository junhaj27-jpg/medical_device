import mimetypes
import zipfile
from pathlib import Path, PurePath

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible

ALLOWLIST = {".pdf":"application/pdf",".docx":"application/vnd.openxmlformats-officedocument.wordprocessingml.document",".xlsx":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".csv":"text/csv"}

@deconstructible
class PrivateMediaStorage(FileSystemStorage):
    def __init__(self): super().__init__(location=settings.PRIVATE_MEDIA_ROOT,base_url=None)

def _detected_mime(data,extension):
    if data.startswith(b"%PDF-"): return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"): return "image/png"
    if data.startswith(b"\xff\xd8\xff"): return "image/jpeg"
    if data.startswith(b"PK\x03\x04") and extension in {".docx",".xlsx"}: return ALLOWLIST[extension]
    if extension==".csv":
        try: data.decode("utf-8-sig"); return "text/csv"
        except UnicodeDecodeError: return "application/octet-stream"
    return "application/octet-stream"

def _validate_zip(file_obj,extension):
    file_obj.seek(0)
    try:
        with zipfile.ZipFile(file_obj) as archive:
            infos=archive.infolist(); total=sum(i.file_size for i in infos); compressed=sum(max(i.compress_size,1) for i in infos)
            if total>settings.ATTACHMENT_MAX_UNCOMPRESSED_SIZE or total/compressed>settings.ATTACHMENT_MAX_COMPRESSION_RATIO: raise ValidationError("압축 해제 크기 또는 압축률이 안전 한도를 초과합니다.")
            for info in infos:
                path=PurePath(info.filename)
                if path.is_absolute() or ".." in path.parts: raise ValidationError("ZIP 내부 경로가 안전하지 않습니다.")
            names={i.filename for i in infos}
            if "[Content_Types].xml" not in names: raise ValidationError("Office 문서 내부 구조가 올바르지 않습니다.")
            prefix="word/" if extension==".docx" else "xl/"
            if not any(name.startswith(prefix) for name in names): raise ValidationError("Office 문서 유형과 내부 구조가 일치하지 않습니다.")
    except zipfile.BadZipFile as exc: raise ValidationError("손상되었거나 잘못된 ZIP 기반 문서입니다.") from exc
    finally: file_obj.seek(0)

def validate_file_content(value):
    name=value.name
    if "\x00" in name or Path(name).name!=name or "/" in name or "\\" in name: raise ValidationError("안전하지 않은 파일명입니다.")
    suffixes=Path(name).suffixes
    if len(suffixes)!=1: raise ValidationError("이중 확장자는 허용되지 않습니다.")
    extension=suffixes[0].lower() if suffixes else ""
    if extension not in ALLOWLIST: raise ValidationError("허용되지 않는 파일 형식입니다.")
    if value.size>settings.ATTACHMENT_MAX_SIZE: raise ValidationError("파일 크기 제한을 초과했습니다.")
    value.seek(0); head=value.read(min(value.size,8192)); value.seek(0); detected=_detected_mime(head,extension)
    if detected!=ALLOWLIST[extension]: raise ValidationError("확장자와 실제 파일 형식이 일치하지 않습니다.")
    supplied=getattr(value,"content_type",None)
    if supplied and supplied not in {detected,"application/octet-stream",mimetypes.guess_type(name)[0]}: raise ValidationError("Content-Type과 실제 파일 형식이 일치하지 않습니다.")
    if extension in {".docx",".xlsx"}: _validate_zip(value,extension)
    return detected

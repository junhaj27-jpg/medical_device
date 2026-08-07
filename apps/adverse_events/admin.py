from django.contrib import admin

from .models import AdverseEvent, Attachment, PatientAnonymousInfo

admin.site.register(AdverseEvent); admin.site.register(PatientAnonymousInfo); admin.site.register(Attachment)

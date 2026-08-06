from django.contrib import admin
from .models import AdverseEvent,PatientAnonymousInfo,Attachment
admin.site.register(AdverseEvent); admin.site.register(PatientAnonymousInfo); admin.site.register(Attachment)

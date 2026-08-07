from django.contrib import admin

from .models import DeviceLot, MedicalDevice

admin.site.register(MedicalDevice); admin.site.register(DeviceLot)

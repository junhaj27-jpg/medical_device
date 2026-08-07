from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets=UserAdmin.fieldsets+(("업무 정보",{"fields":("role","department","phone","created_at")}),)
    readonly_fields=("created_at",)
    list_display=("username","email","role","department","is_active")

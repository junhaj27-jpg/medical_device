from django.contrib import admin

from apps.audit.services import record_audit

from .models import DestructionRequest, LegalHold, RetentionPolicy


@admin.register(RetentionPolicy)
class RetentionPolicyAdmin(admin.ModelAdmin):
    list_display=("record_type","version","effective_from","retention_days","created_by")
    def get_readonly_fields(self,request,obj=None): return [f.name for f in self.model._meta.fields] if obj else ["created_by"]
    def save_model(self,request,obj,form,change):
        obj.created_by=request.user; super().save_model(request,obj,form,change); record_audit(user=request.user,action="RETENTION_POLICY_CREATE",target=obj,reason="관리자 보존정책 버전 생성",request=request)
    def has_delete_permission(self,request,obj=None): return False

class WorkflowReadOnlyAdmin(admin.ModelAdmin):
    def get_readonly_fields(self,request,obj=None): return [f.name for f in self.model._meta.fields]
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False

admin.site.register(LegalHold,WorkflowReadOnlyAdmin)
admin.site.register(DestructionRequest,WorkflowReadOnlyAdmin)

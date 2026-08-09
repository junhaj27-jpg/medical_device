from django.contrib import admin

from .models import Approval, ElectronicSignature, SignatureRevocation

admin.site.register(Approval)


class ImmutableAdmin(admin.ModelAdmin):
    readonly_fields = ()
    def get_readonly_fields(self, request, obj=None): return [f.name for f in self.model._meta.fields]
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


admin.site.register(ElectronicSignature, ImmutableAdmin)
admin.site.register(SignatureRevocation, ImmutableAdmin)

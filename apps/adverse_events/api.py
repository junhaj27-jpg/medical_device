from rest_framework import permissions, viewsets

from .models import AdverseEvent
from .serializers import AdverseEventSerializer


class EventPermission(permissions.BasePermission):
    def has_permission(self,request,view): return request.user.is_authenticated and (request.method in permissions.SAFE_METHODS or request.user.role in {"STAFF","RA_QA","ADMIN"})
    def has_object_permission(self,request,view,obj): return request.user.role!="STAFF" or obj.reporter_id==request.user.id
class AdverseEventViewSet(viewsets.ModelViewSet):
    serializer_class=AdverseEventSerializer; permission_classes=[EventPermission]
    def get_queryset(self):
        qs=AdverseEvent.objects.select_related("medical_device","device_lot")
        return qs.filter(reporter=self.request.user) if self.request.user.role=="STAFF" else qs
    def perform_create(self,serializer): serializer.save(reporter=self.request.user,status="RECEIVED")

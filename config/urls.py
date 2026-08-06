from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include,path
from drf_spectacular.views import SpectacularAPIView,SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from apps.adverse_events.api import AdverseEventViewSet
from apps.dashboard import views
router=DefaultRouter(); router.register("events",AdverseEventViewSet,basename="api-event")
urlpatterns=[path("admin/",admin.site.urls),path("",auth_views.LoginView.as_view(template_name="login.html"),name="login"),path("logout/",auth_views.LogoutView.as_view(),name="logout"),path("dashboard/",views.dashboard,name="dashboard"),path("events/",views.event_list,name="event_list"),path("events/new/",views.event_create,name="event_create"),path("events/<int:pk>/",views.event_detail,name="event_detail"),path("events/<int:pk>/report/",views.report_download,name="report_download"),path("devices/",views.devices,name="devices"),path("capas/",views.capas,name="capas"),path("audit/",views.audits,name="audits"),path("api/",include(router.urls)),path("api/schema/",SpectacularAPIView.as_view(),name="schema"),path("api/docs/",SpectacularSwaggerView.as_view(url_name="schema"),name="swagger-ui")]+static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)

from django.urls import path
from . import views
app_name="capa"
urlpatterns=[path("",views.capa_list,name="list"),path("create/",views.capa_create,name="create"),path("<int:pk>/",views.capa_detail,name="detail"),path("<int:pk>/edit/",views.capa_edit,name="edit"),path("<int:pk>/status/",views.capa_status,name="status")]

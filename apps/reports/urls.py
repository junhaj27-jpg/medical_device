from django.urls import path

from . import views

app_name="reports"
urlpatterns=[path("",views.report_list,name="list"),path("create/",views.report_create,name="create"),path("<int:pk>/",views.report_detail,name="detail"),path("<int:pk>/edit/",views.report_edit,name="edit"),path("<int:pk>/download/",views.report_download,name="download"),path("<int:pk>/<str:action>/",views.report_action,name="action")]

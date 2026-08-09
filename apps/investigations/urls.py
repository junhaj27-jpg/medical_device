from django.urls import path

from . import views

app_name="investigations"
urlpatterns=[path("<int:pk>/",views.detail,name="detail"),path("<int:pk>/approval/<str:action>/",views.approval,name="approval")]

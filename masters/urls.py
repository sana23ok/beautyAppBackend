from django.urls import path

from . import views

app_name = 'masters'

urlpatterns = [
    path('api/masters/', views.masters_list, name='masters_list'),
    path('api/masters/<int:pk>/', views.master_detail, name='master_detail'),
]

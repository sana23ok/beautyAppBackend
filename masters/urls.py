from django.urls import path

from . import views

app_name = 'masters'

urlpatterns = [
    path('api/masters/', views.masters_list, name='masters_list'),
    path('api/masters/me/', views.my_master_profile, name='my_master_profile'),
    path('api/masters/me/week-schedules/', views.my_week_schedules, name='my_week_schedules'),
    path(
        'api/masters/me/week-schedules/<int:schedule_id>/',
        views.my_week_schedule_detail,
        name='my_week_schedule_detail',
    ),
    path(
        'api/masters/<int:pk>/week-schedules/',
        views.master_week_schedules_public,
        name='master_week_schedules_public',
    ),
    path('api/masters/<int:pk>/', views.master_detail, name='master_detail'),
]

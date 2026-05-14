from django.urls import path

from . import views

app_name = 'masters'

urlpatterns = [
    path('api/masters/', views.masters_list, name='masters_list'),
    path('api/masters/me/', views.my_master_profile, name='my_master_profile'),
    path('api/masters/me/services/', views.my_master_services, name='my_master_services'),
    path(
        'api/masters/me/services/<int:service_id>/',
        views.my_master_service_detail,
        name='my_master_service_detail',
    ),
    path('api/masters/me/work_photos/', views.my_work_photos, name='my_work_photos'),
    path(
        'api/masters/me/work_photos/<int:photo_id>/',
        views.my_work_photo_detail,
        name='my_work_photo_detail',
    ),
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
    path('api/masters/<int:pk>/reviews/', views.master_reviews, name='master_reviews'),
    path('api/masters/<int:pk>/reviews/<int:review_id>/report/', views.report_review, name='report_review'),
    path('api/masters/<int:pk>/', views.master_detail, name='master_detail'),
]

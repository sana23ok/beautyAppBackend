from django.urls import path

from . import views

app_name = 'bookings'

urlpatterns = [
    path('api/bookings/available-slots/', views.available_slots, name='available_slots'),
    path('api/bookings/master/<int:master_id>/', views.master_bookings, name='master_bookings'),
    path('api/bookings/my/', views.my_bookings, name='my_bookings'),
    path('api/bookings/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('api/bookings/', views.create_booking, name='create_booking'),
]

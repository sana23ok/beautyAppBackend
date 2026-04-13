from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('master', 'service', 'client', 'appointment_date', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'appointment_date', 'master')
    search_fields = ('master__name', 'service__name', 'client__username', 'client__email')

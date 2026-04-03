from django.contrib import admin

from .models import Master, MasterWeekTimetable, MasterWorkPhoto


class MasterWorkPhotoInline(admin.TabularInline):
    model = MasterWorkPhoto
    extra = 1
    fields = ('photo_url', 'caption')


class MasterWeekTimetableInline(admin.TabularInline):
    model = MasterWeekTimetable
    extra = 0
    fields = (
        'week_start',
        'monday_hours',
        'tuesday_hours',
        'wednesday_hours',
        'thursday_hours',
        'friday_hours',
        'saturday_hours',
        'sunday_hours',
    )


@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialization', 'city', 'experience_years', 'rating', 'is_active')
    list_filter = ('specialization', 'city', 'is_active')
    search_fields = ('name', 'specialization', 'city')
    inlines = [MasterWorkPhotoInline, MasterWeekTimetableInline]


@admin.register(MasterWeekTimetable)
class MasterWeekTimetableAdmin(admin.ModelAdmin):
    list_display = ('master', 'week_start', 'updated_at')
    list_filter = ('master',)
    date_hierarchy = 'week_start'
    search_fields = ('master__name',)


@admin.register(MasterWorkPhoto)
class MasterWorkPhotoAdmin(admin.ModelAdmin):
    list_display = ('master', 'caption', 'uploaded_at')
    list_filter = ('master',)

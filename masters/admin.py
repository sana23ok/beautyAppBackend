from django.contrib import admin

from .models import Master, MasterWorkPhoto


class MasterWorkPhotoInline(admin.TabularInline):
    model = MasterWorkPhoto
    extra = 1
    fields = ('photo_url', 'caption')


@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialization', 'city', 'experience_years', 'rating', 'is_active')
    list_filter = ('specialization', 'city', 'is_active')
    search_fields = ('name', 'specialization', 'city')
    inlines = [MasterWorkPhotoInline]


@admin.register(MasterWorkPhoto)
class MasterWorkPhotoAdmin(admin.ModelAdmin):
    list_display = ('master', 'caption', 'uploaded_at')
    list_filter = ('master',)

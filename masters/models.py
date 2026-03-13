from django.contrib.auth.models import User
from django.db import models


class Master(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='master_profile',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255, blank=True, default='')
    city = models.CharField(max_length=255, blank=True, default='')
    address = models.CharField(max_length=500, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    profile_photo = models.URLField(blank=True)
    monday_hours = models.CharField(max_length=100, blank=True, default='')
    tuesday_hours = models.CharField(max_length=100, blank=True, default='')
    wednesday_hours = models.CharField(max_length=100, blank=True, default='')
    thursday_hours = models.CharField(max_length=100, blank=True, default='')
    friday_hours = models.CharField(max_length=100, blank=True, default='')
    saturday_hours = models.CharField(max_length=100, blank=True, default='')
    sunday_hours = models.CharField(max_length=100, blank=True, default='')
    rating = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-rating', 'name']

    def __str__(self):
        return f'{self.name} — {self.specialization}'


class MasterWorkPhoto(models.Model):
    master = models.ForeignKey(Master, on_delete=models.CASCADE, related_name='work_photos')
    photo_url = models.URLField()
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'Photo for {self.master.name}'

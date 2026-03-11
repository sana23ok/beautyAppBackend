from django.db import models


class Master(models.Model):
    name = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    address = models.CharField(max_length=500, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    profile_photo = models.URLField(blank=True)
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

from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    google_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    avatar = models.URLField(blank=True, null=True)
    phone_number = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f'Profile({self.user.email})'


class Client(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='client_profile',
        null=True,
        blank=True,
    )

    # personal information
    name = models.CharField(max_length=255)
    user_name = models.CharField(max_length=255, blank=True, default='')
    email = models.EmailField()
    phone_number = models.CharField(max_length=255, blank=True, default='')
    location = models.CharField(max_length=255, blank=True, default='')

    # appearance analysis base info
    age = models.IntegerField(null=True, blank=True)
    height_sm = models.IntegerField(null=True, blank=True)
    eyes_color = models.CharField(max_length=255, blank=True, default='')
    skin_color = models.CharField(max_length=255, blank=True, default='')
    hair_color = models.CharField(max_length=255, blank=True, default='')

    image_url = models.URLField(blank=True)

    # face morphology
    face_shape = models.CharField(max_length=255, blank=True, default='')
    forehead_height = models.CharField(max_length=255, blank=True)
    eye_shape = models.CharField(max_length=255, blank=True, default='')
    eye_size = models.CharField(max_length=255, blank=True)
    nose_shape = models.CharField(max_length=255, blank=True)
    lips_fullness = models.CharField(max_length=255, blank=True, default='')
    chin_shape = models.CharField(max_length=255, blank=True)
    brow_thickness = models.CharField(max_length=255, blank=True, default='')
    brow_arch = models.CharField(max_length=255, blank=True)

    # color metrics
    undertone = models.CharField(max_length=255, blank=True)
    freckles = models.BooleanField(default=False)
    tanning_reaction = models.CharField(max_length=255, blank=True)

    # body type
    shoulders_width = models.CharField(max_length=255, blank=True)
    bust = models.IntegerField(null=True)
    waist = models.IntegerField(null=True)
    hips = models.IntegerField(null=True)
    leg_length_ratio = models.CharField(max_length=255, blank=True)

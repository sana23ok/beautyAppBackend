from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    google_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    avatar = models.URLField(blank=True, null=True)
    phone_number = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f'Profile({self.user.email})'


class EmailVerificationCode(models.Model):
    email = models.EmailField(unique=True)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f'EmailVerificationCode({self.email})'


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


class FavoriteMaster(models.Model):
    """Client user marks masters as favorites; persisted server-side."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_masters')
    master = models.ForeignKey(
        'masters.Master',
        on_delete=models.CASCADE,
        related_name='favorited_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'master'],
                name='users_favoritemaster_user_master_uniq',
            ),
        ]

    def __str__(self):
        return f'{self.user_id} ♥ {self.master_id}'


class UserReport(models.Model):
    """A user's complaint about another user's profile/account."""

    REASON_SPAM = 'spam'
    REASON_FAKE = 'fake_profile'
    REASON_OFFENSIVE = 'offensive'
    REASON_HARASSMENT = 'harassment'
    REASON_OTHER = 'other'

    REASON_CHOICES = [
        (REASON_SPAM, 'Spam'),
        (REASON_FAKE, 'Fake profile'),
        (REASON_OFFENSIVE, 'Offensive content'),
        (REASON_HARASSMENT, 'Harassment / bullying'),
        (REASON_OTHER, 'Other'),
    ]

    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile_reports_received')
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile_reports_made')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    text = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['target', 'reporter'],
                name='users_userreport_target_reporter_uniq',
            ),
        ]

    def __str__(self):
        return f'Report #{self.id}: user {self.target_id} by {self.reporter_id} ({self.reason})'

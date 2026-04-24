from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
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
    review_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    iban = models.CharField(max_length=64, blank=True, default='')
    payment_purpose = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-rating', 'name']

    def __str__(self):
        return f'{self.name} — {self.specialization}'

    @classmethod
    def sync_review_aggregates_for_master_id(cls, master_id):
        """Recompute denormalized rating + review_count from MasterReview rows (single aggregate query)."""
        from django.db.models import Avg, Count

        agg = MasterReview.objects.filter(master_id=master_id).aggregate(
            cnt=Count('id'),
            avg=Avg('rating'),
        )
        n = agg['cnt'] or 0
        raw = agg['avg']
        rating = float(raw) if raw is not None and n > 0 else 0.0
        cls.objects.filter(pk=master_id).update(review_count=n, rating=rating)


class MasterService(models.Model):
    """Price list row: service name, UAH price, optional duration."""

    master = models.ForeignKey(
        Master,
        on_delete=models.CASCADE,
        related_name='services',
    )
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration_minutes = models.PositiveIntegerField(default=0)
    requires_prepayment = models.BooleanField(default=False)
    # False = historical row kept for booking FK integrity; True = shown in active price list
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.name} ({self.master.name})'


class MasterWorkPhoto(models.Model):
    master = models.ForeignKey(Master, on_delete=models.CASCADE, related_name='work_photos')
    photo_url = models.URLField()
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'Photo for {self.master.name}'


class MasterWeekTimetable(models.Model):
    """
    Per-week working hours for a master. week_start is the Monday (inclusive) of that week.
    Used for schedules that differ by week; default template hours stay on Master.
    """
    master = models.ForeignKey(
        Master,
        on_delete=models.CASCADE,
        related_name='week_timetables',
    )
    week_start = models.DateField(db_index=True)
    monday_hours = models.CharField(max_length=100, blank=True, default='')
    tuesday_hours = models.CharField(max_length=100, blank=True, default='')
    wednesday_hours = models.CharField(max_length=100, blank=True, default='')
    thursday_hours = models.CharField(max_length=100, blank=True, default='')
    friday_hours = models.CharField(max_length=100, blank=True, default='')
    saturday_hours = models.CharField(max_length=100, blank=True, default='')
    sunday_hours = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['week_start']
        constraints = [
            models.UniqueConstraint(
                fields=('master', 'week_start'),
                name='unique_master_week_start',
            ),
        ]

    def __str__(self):
        return f'{self.master.name} — week of {self.week_start}'


class MasterReview(models.Model):
    """Client review after a completed visit (see API eligibility: past non-cancelled booking)."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='master_reviews_written',
    )
    master = models.ForeignKey(
        Master,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=('author', 'master'), name='unique_review_per_author_master'),
        ]

    def __str__(self):
        return f'{self.author_id} → {self.master_id}: {self.rating}★'

from django.contrib.auth.models import User
from django.db import models


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    master = models.ForeignKey(
        'masters.Master',
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    service = models.ForeignKey(
        'masters.MasterService',
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    appointment_date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    notes = models.CharField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['appointment_date', 'start_time', 'id']

    def __str__(self):
        return f'{self.master.name} · {self.service.name} · {self.appointment_date} {self.start_time}'

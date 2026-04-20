from datetime import datetime, timedelta
import re

from rest_framework import serializers

from .models import Booking
from masters.models import Master, MasterService, MasterWeekTimetable


DAY_FIELDS = (
    'monday_hours',
    'tuesday_hours',
    'wednesday_hours',
    'thursday_hours',
    'friday_hours',
    'saturday_hours',
    'sunday_hours',
)
NUMBER_PATTERN = re.compile(r'\d{1,2}')


def _bounds_from_hours(raw_hours):
    numbers = [int(match.group()) for match in NUMBER_PATTERN.finditer((raw_hours or '').strip())]
    if len(numbers) < 2:
        return None
    start_hour = max(0, min(numbers[0], 23))
    end_hour = max(0, min(numbers[1], 24))
    if start_hour >= end_hour:
        return None
    return start_hour, end_hour


def _week_row_for_date(master, appointment_date):
    monday = appointment_date - timedelta(days=appointment_date.weekday())
    return MasterWeekTimetable.objects.filter(master=master, week_start=monday).first()


def _working_bounds_for_date(master, appointment_date):
    field_name = DAY_FIELDS[appointment_date.weekday()]
    week_row = _week_row_for_date(master, appointment_date)
    source = week_row if week_row is not None else master
    return _bounds_from_hours(getattr(source, field_name, ''))


def _combine(appointment_date, time_value):
    return datetime.combine(appointment_date, time_value)


def _active_bookings_queryset(master, appointment_date):
    return Booking.objects.filter(
        master=master,
        appointment_date=appointment_date,
    ).exclude(status=Booking.Status.CANCELLED)


def allowed_starts_for_service(master, service, appointment_date):
    bounds = _working_bounds_for_date(master, appointment_date)
    if bounds is None or service.duration_minutes <= 0:
        return []

    start_hour, end_hour = bounds
    day_start = datetime.combine(appointment_date, datetime.min.time()).replace(hour=start_hour, minute=0)
    day_end = datetime.combine(appointment_date, datetime.min.time()).replace(hour=end_hour, minute=0)
    duration = timedelta(minutes=service.duration_minutes)

    candidates = {
        day_start + timedelta(hours=offset)
        for offset in range(max(0, end_hour - start_hour))
    }

    for booking in _active_bookings_queryset(master, appointment_date):
        booking_end = _combine(appointment_date, booking.end_time)
        if day_start <= booking_end < day_end and booking_end.minute in (0, 30):
            candidates.add(booking_end)

    available = []
    existing = list(_active_bookings_queryset(master, appointment_date))
    for candidate in sorted(candidates):
        if candidate.minute not in (0, 30):
            continue
        candidate_end = candidate + duration
        if candidate_end > day_end:
            continue
        overlaps = any(
            candidate < _combine(appointment_date, booking.end_time)
            and candidate_end > _combine(appointment_date, booking.start_time)
            for booking in existing
        )
        if not overlaps:
            available.append(candidate.time().replace(second=0, microsecond=0))
    return available


class BookingSerializer(serializers.ModelSerializer):
    client = serializers.IntegerField(source='client.id', read_only=True)
    client_name = serializers.SerializerMethodField()
    client_avatar = serializers.SerializerMethodField()
    client_phone = serializers.SerializerMethodField()
    master_name = serializers.CharField(source='master.name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_duration_minutes = serializers.IntegerField(source='service.duration_minutes', read_only=True)
    master_city = serializers.CharField(source='master.city', read_only=True)
    master_address = serializers.CharField(source='master.address', read_only=True)

    class Meta:
        model = Booking
        fields = (
            'id',
            'client',
            'client_name',
            'client_avatar',
            'client_phone',
            'master',
            'master_name',
            'master_city',
            'master_address',
            'service',
            'service_name',
            'service_duration_minutes',
            'appointment_date',
            'start_time',
            'end_time',
            'status',
            'notes',
            'created_at',
        )
        read_only_fields = fields

    def get_client_name(self, obj):
        user = obj.client
        if not user:
            return ''
        full = f"{user.first_name} {user.last_name}".strip()
        if full:
            return full
        return user.username or user.email or f"User {user.id}"

    def get_client_avatar(self, obj):
        user = obj.client
        if not user:
            return ''
        try:
            avatar = user.profile.avatar
            if avatar:
                return avatar
        except Exception:
            pass
        return ''

    def get_client_phone(self, obj):
        user = obj.client
        if not user:
            return ''
        try:
            return user.profile.phone_number or ''
        except Exception:
            return ''


class BookingCreateSerializer(serializers.Serializer):
    master_id = serializers.IntegerField()
    service_id = serializers.IntegerField()
    appointment_date = serializers.DateField()
    start_time = serializers.TimeField(format='%H:%M', input_formats=['%H:%M', '%H:%M:%S'])
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        master = Master.objects.filter(pk=attrs['master_id'], is_active=True).first()
        if master is None:
            raise serializers.ValidationError({'master_id': 'Master not found.'})

        service = MasterService.objects.filter(pk=attrs['service_id'], master=master).first()
        if service is None:
            raise serializers.ValidationError({'service_id': 'Service not found for this master.'})
        if service.duration_minutes <= 0:
            raise serializers.ValidationError({'service_id': 'Selected service has no duration.'})

        start_time = attrs['start_time']
        if start_time.minute not in (0, 30) or start_time.second != 0:
            raise serializers.ValidationError({'start_time': 'Start time must be on :00 or :30.'})

        allowed = allowed_starts_for_service(master, service, attrs['appointment_date'])
        if start_time not in allowed:
            raise serializers.ValidationError({'start_time': 'This time is no longer available.'})

        start_dt = _combine(attrs['appointment_date'], start_time)
        end_dt = start_dt + timedelta(minutes=service.duration_minutes)

        attrs['master'] = master
        attrs['service'] = service
        attrs['end_time'] = end_dt.time().replace(second=0, microsecond=0)
        return attrs

    def create(self, validated_data):
        return Booking.objects.create(
            client=self.context['request'].user,
            master=validated_data['master'],
            service=validated_data['service'],
            appointment_date=validated_data['appointment_date'],
            start_time=validated_data['start_time'],
            end_time=validated_data['end_time'],
            notes=validated_data.get('notes', ''),
        )

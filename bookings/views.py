from django.db import DatabaseError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import DateField

from .models import Booking
from .serializers import BookingCreateSerializer, BookingSerializer, allowed_starts_for_service
from masters.models import Master, MasterService


@api_view(['GET'])
@permission_classes([AllowAny])
def available_slots(request):
    try:
        master_id = int(request.query_params.get('master_id', '0'))
        service_id = int(request.query_params.get('service_id', '0'))
    except ValueError:
        return Response({'error': 'master_id and service_id must be integers.'}, status=status.HTTP_400_BAD_REQUEST)

    appointment_date = request.query_params.get('date')
    if not appointment_date:
        return Response({'error': 'date is required.'}, status=status.HTTP_400_BAD_REQUEST)
    master = Master.objects.filter(pk=master_id, is_active=True).first()
    if master is None:
        return Response({'error': 'Master not found.'}, status=status.HTTP_404_NOT_FOUND)
    service = MasterService.objects.filter(pk=service_id, master=master).first()
    if service is None:
        return Response({'error': 'Service not found for this master.'}, status=status.HTTP_404_NOT_FOUND)
    try:
        parsed_date = DateField().to_internal_value(appointment_date)
    except Exception:
        return Response({'error': 'Invalid date.'}, status=status.HTTP_400_BAD_REQUEST)
    slots = [value.strftime('%H:%M') for value in allowed_starts_for_service(master, service, parsed_date)]
    return Response(
        {
            'master_id': master.id,
            'service_id': service.id,
            'date': parsed_date.isoformat(),
            'slots': slots,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def master_bookings(request, master_id):
    master = Master.objects.filter(pk=master_id, is_active=True).first()
    if master is None:
        return Response({'error': 'Master not found.'}, status=status.HTTP_404_NOT_FOUND)

    bookings = Booking.objects.filter(master=master).exclude(status=Booking.Status.CANCELLED)
    from_date = request.query_params.get('from')
    to_date = request.query_params.get('to')
    if from_date:
        bookings = bookings.filter(appointment_date__gte=from_date)
    if to_date:
        bookings = bookings.filter(appointment_date__lte=to_date)
    return Response(BookingSerializer(bookings, many=True).data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_bookings(request):
    bookings = Booking.objects.filter(client=request.user).exclude(status=Booking.Status.CANCELLED)
    return Response(BookingSerializer(bookings, many=True).data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_booking(request):
    serializer = BookingCreateSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    try:
        booking = serializer.save()
    except DatabaseError:
        return Response(
            {'detail': 'Database error while creating booking. Run migrations on the server: python manage.py migrate'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)

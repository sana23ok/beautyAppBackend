import logging
import os

from django.conf import settings
from django.db import DatabaseError, IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Master, MasterService, MasterWeekTimetable, MasterWorkPhoto
from .serializers import (
    MasterSerializer,
    MasterServiceSerializer,
    MasterWeekTimetableSerializer,
    MasterWorkPhotoSerializer,
    MasterWriteSerializer,
)

MAX_WORK_PHOTOS = 50


logger = logging.getLogger(__name__)


def _apply_master_search(queryset, raw_query):
    """
    Split the incoming text into keywords and require each keyword to match at
    least one searchable field. This lets queries like "kyiv nails" match
    masters by city + specialization.
    """
    if not raw_query:
        return queryset

    keywords = [keyword.strip() for keyword in raw_query.split() if keyword.strip()]
    for keyword in keywords:
        queryset = queryset.filter(
            Q(name__icontains=keyword)
            | Q(city__icontains=keyword)
            | Q(specialization__icontains=keyword)
            | Q(description__icontains=keyword)
        )
    return queryset


# ── Masters list + create ─────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def masters_list(request):
    """
    GET  /api/masters/  — Returns active master profiles from the database.
                           Supports keyword search with `q` or `search`.
    POST /api/masters/  — Creates a new master profile.

    Search examples:
        /api/masters/?q=київ манікюр
        /api/masters/?search=lash lviv

    POST body example:
    {
        "name": "Анна Іваненко",
        "specialization": "Майстер манікюру",
        "city": "Київ",
        "address": "вул. Хрещатик, 1",
        "experience_years": 5,
        "description": "Досвідчений майстер з портфоліо...",
        "profile_photo": "https://example.com/photo.jpg",
        "work_photos": [
            {"photo_url": "https://example.com/work1.jpg", "caption": "Манікюр"},
            {"photo_url": "https://example.com/work2.jpg", "caption": "Педикюр"}
        ]
    }
    """
    if request.method == 'GET':
        search_query = request.query_params.get('q') or request.query_params.get('search', '')
        masters = (
            Master.objects.select_related('user', 'user__profile')
            .prefetch_related('work_photos', 'week_timetables', 'services')
            .filter(is_active=True)
        )
        masters = _apply_master_search(masters, search_query).distinct()
        serializer = MasterSerializer(masters, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'POST':
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required to create a master profile.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if Master.objects.filter(user=request.user).exists():
            return Response(
                {'error': 'This user already has a master profile.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MasterWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        master = serializer.save(user=request.user)
        return Response(MasterSerializer(master).data, status=status.HTTP_201_CREATED)


# ── Single master detail ──────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def master_detail(request, pk):
    """
    GET /api/masters/<id>/  — Returns full profile of a single master
                              including all work photos.
    """
    try:
        master = (
            Master.objects.select_related('user', 'user__profile')
            .prefetch_related('work_photos', 'week_timetables', 'services')
            .get(pk=pk)
        )
    except Master.DoesNotExist:
        return Response({'error': 'Master not found.'}, status=status.HTTP_404_NOT_FOUND)

    return Response(MasterSerializer(master).data, status=status.HTTP_200_OK)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def my_master_profile(request):
    """
    GET   /api/masters/me/  — Returns the current user's master profile.
    PATCH /api/masters/me/  — Updates the current user's master profile.
    """
    try:
        master = (
            Master.objects.select_related('user', 'user__profile')
            .prefetch_related('work_photos', 'week_timetables', 'services')
            .get(user=request.user)
        )
    except Master.DoesNotExist:
        return Response({'error': 'No master profile found for this user.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(MasterSerializer(master).data, status=status.HTTP_200_OK)

    serializer = MasterWriteSerializer(master, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        master = serializer.save()
    except DatabaseError:
        logger.exception('Failed to save master profile')
        return Response(
            {
                'detail': 'Database error while saving profile. Run migrations on the server: python manage.py migrate',
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    master = (
        Master.objects.select_related('user', 'user__profile')
        .prefetch_related('work_photos', 'week_timetables', 'services')
        .get(pk=master.pk)
    )
    return Response(MasterSerializer(master).data, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def my_master_services(request):
    """
    GET  /api/masters/me/services/ — Returns the current master's active price list.
    POST /api/masters/me/services/ — Creates a single new service row.
    """
    try:
        master = request.user.master_profile
    except Master.DoesNotExist:
        return Response({'error': 'No master profile found for this user.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        queryset = master.services.filter(is_active=True).order_by('id')
        return Response(MasterServiceSerializer(queryset, many=True).data, status=status.HTTP_200_OK)

    # POST — create one service
    serializer = MasterServiceSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    try:
        service = serializer.save(master=master, is_active=True)
    except DatabaseError:
        return Response(
            {'detail': 'Database error while saving service. Run migrations on the server: python manage.py migrate'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response(MasterServiceSerializer(service).data, status=status.HTTP_201_CREATED)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def my_master_service_detail(request, service_id):
    """
    PATCH  /api/masters/me/services/<id>/ — Update a single service row (partial).
    DELETE /api/masters/me/services/<id>/ — Remove a service from the price list.
                                            If bookings reference it, the row is kept
                                            in the DB (is_active=False) so no bookings
                                            are lost; otherwise the row is hard-deleted.
    """
    try:
        master = request.user.master_profile
    except Master.DoesNotExist:
        return Response({'error': 'No master profile found for this user.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        service = MasterService.objects.get(pk=service_id, master=master, is_active=True)
    except MasterService.DoesNotExist:
        return Response({'error': 'Service not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        try:
            if service.bookings.exists():
                service.is_active = False
                service.save(update_fields=['is_active'])
            else:
                service.delete()
        except DatabaseError:
            return Response(
                {'detail': 'Database error while deleting service.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH
    serializer = MasterServiceSerializer(service, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    try:
        serializer.save()
    except DatabaseError:
        return Response(
            {'detail': 'Database error while updating service.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response(serializer.data, status=status.HTTP_200_OK)


# ── Per-week timetables (available weeks) ─────────────────────────────────────


def _week_schedule_queryset_for_master(master, request):
    qs = MasterWeekTimetable.objects.filter(master=master).order_by('week_start')
    from_s = request.query_params.get('from') or request.query_params.get('from_date')
    to_s = request.query_params.get('to') or request.query_params.get('to_date')
    if from_s:
        qs = qs.filter(week_start__gte=from_s)
    if to_s:
        qs = qs.filter(week_start__lte=to_s)
    return qs


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def my_week_schedules(request):
    """
    GET  /api/masters/me/week-schedules/  — List this master's week rows (?from=&to= optional).
    POST — Create or replace one week (body: week_start Monday + day hours).
    """
    try:
        master = request.user.master_profile
    except Master.DoesNotExist:
        return Response({'error': 'No master profile found for this user.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        qs = _week_schedule_queryset_for_master(master, request)
        return Response(MasterWeekTimetableSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    serializer = MasterWeekTimetableSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    try:
        serializer.save(master=master)
    except IntegrityError:
        return Response(
            {'error': 'A timetable for this week already exists. Use PATCH on that row or delete it first.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def my_week_schedule_detail(request, schedule_id):
    try:
        master = request.user.master_profile
    except Master.DoesNotExist:
        return Response({'error': 'No master profile found for this user.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        row = MasterWeekTimetable.objects.get(pk=schedule_id, master=master)
    except MasterWeekTimetable.DoesNotExist:
        return Response({'error': 'Week schedule not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(MasterWeekTimetableSerializer(row).data, status=status.HTTP_200_OK)

    if request.method == 'DELETE':
        row.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = MasterWeekTimetableSerializer(row, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    try:
        serializer.save()
    except IntegrityError:
        return Response(
            {'error': 'A timetable for this week already exists.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def master_week_schedules_public(request, pk):
    """
    GET /api/masters/<id>/week-schedules/ — Read-only week timetables for booking UI.
    """
    try:
        master = Master.objects.get(pk=pk, is_active=True)
    except Master.DoesNotExist:
        return Response({'error': 'Master not found.'}, status=status.HTTP_404_NOT_FOUND)

    qs = _week_schedule_queryset_for_master(master, request)
    return Response(MasterWeekTimetableSerializer(qs, many=True).data, status=status.HTTP_200_OK)


# ── Work portfolio photos (add / delete) ──────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def my_work_photos(request):
    """
    GET  /api/masters/me/work_photos/ — list the current master's portfolio photos.
    POST /api/masters/me/work_photos/ — upload a new portfolio photo (multipart).
                                        Form fields:
                                          photo   — image file (required)
                                          caption — optional text
                                        Enforces a per-master cap of MAX_WORK_PHOTOS.
    """
    try:
        master = request.user.master_profile
    except Master.DoesNotExist:
        return Response(
            {'error': 'No master profile found for this user.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == 'GET':
        queryset = master.work_photos.all()
        return Response(
            MasterWorkPhotoSerializer(queryset, many=True).data,
            status=status.HTTP_200_OK,
        )

    if master.work_photos.count() >= MAX_WORK_PHOTOS:
        return Response(
            {'error': f'Maximum {MAX_WORK_PHOTOS} work photos reached. Delete some before uploading more.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    photo = request.FILES.get('photo')
    if not photo:
        return Response(
            {'error': 'No photo file provided. Use form field "photo".'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    allowed_types = ('image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/heic')
    if photo.content_type not in allowed_types:
        return Response(
            {'error': f'Invalid file type. Allowed: {", ".join(allowed_types)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if photo.size > 10 * 1024 * 1024:
        return Response(
            {'error': 'File too large. Maximum size is 10 MB.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', '') or ''
    api_key = getattr(settings, 'CLOUDINARY_API_KEY', '') or ''
    api_secret = getattr(settings, 'CLOUDINARY_API_SECRET', '') or ''
    cloudinary_url = getattr(settings, 'CLOUDINARY_URL', '') or os.getenv('CLOUDINARY_URL', '')
    if not all([cloud_name, api_key, api_secret]) and not cloudinary_url:
        return Response(
            {'error': 'Cloudinary is not configured on the server.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    try:
        import cloudinary
        import cloudinary.uploader

        if cloudinary_url:
            os.environ['CLOUDINARY_URL'] = cloudinary_url
            cloudinary.config()
        else:
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
            )

        result = cloudinary.uploader.upload(
            photo,
            folder='master_work_photos',
            asset_folder='master_work_photos',
            resource_type='image',
        )
        url = result.get('secure_url') or result.get('url', '')
        if not url:
            return Response(
                {'error': 'Cloudinary did not return a URL.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    except Exception as exc:
        logger.exception('Failed to upload work photo to Cloudinary')
        return Response(
            {'error': f'Upload failed: {exc}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    caption = (request.data.get('caption') or '').strip()[:255]
    record = MasterWorkPhoto.objects.create(
        master=master,
        photo_url=url,
        caption=caption,
    )
    return Response(
        MasterWorkPhotoSerializer(record).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def my_work_photo_detail(request, photo_id):
    """
    DELETE /api/masters/me/work_photos/<id>/ — delete one of the current master's photos.
    """
    try:
        master = request.user.master_profile
    except Master.DoesNotExist:
        return Response(
            {'error': 'No master profile found for this user.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        photo = MasterWorkPhoto.objects.get(pk=photo_id, master=master)
    except MasterWorkPhoto.DoesNotExist:
        return Response(
            {'error': 'Work photo not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    photo.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── Connection test (kept for compatibility) ──────────────────────────────────

def test_connection(request):
    return JsonResponse({
        "message": "🎉 Ура! Android успішно з'єднався з Django!",
        "status": "success"
    })

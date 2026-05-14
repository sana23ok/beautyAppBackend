import hashlib
import os
import random
from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from django.db.models import Count, Q
from masters.models import Master, MasterReview
from masters.serializers import MasterPublicCardSerializer

from .models import Client, EmailVerificationCode, FavoriteMaster, UserProfile, UserReport
from .serializers import (
    ClientSerializer,
    FavoriteToggleSerializer,
    GoogleAuthSerializer,
    LoginSerializer,
    ModerationReviewSerializer,
    ModerationUserSerializer,
    RegisterSerializer,
    SendVerificationCodeSerializer,
    UserUpdateSerializer,
    UserSerializer,
    UserReportSerializer,
)


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


def _user_with_relations(user):
    """Load user with OneToOne relations so serializers read Cloudinary URLs without N+1 bugs."""
    return User.objects.select_related('profile', 'master_profile', 'client_profile').get(pk=user.pk)


def _auth_response(user):
    user = _user_with_relations(user)
    return {
        'user': UserSerializer(user).data,
        'tokens': _tokens_for_user(user),
    }


def _ensure_client_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    client, _ = Client.objects.get_or_create(
        user=user,
        defaults={
            'name': user.get_full_name().strip() or user.email,
            'email': user.email,
            'phone_number': profile.phone_number,
        },
    )
    client.name = user.get_full_name().strip() or user.email
    client.email = user.email
    client.phone_number = profile.phone_number
    client.save()
    return client


def _hash_verification_code(email, code):
    payload = f'{settings.SECRET_KEY}:{email.lower()}:{code}'
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _verification_email_html(code):
    return f"""
<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#F0F9E8;font-family:Arial,Helvetica,sans-serif;color:#3D5A1E;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#F0F9E8;padding:28px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px;background:#ffffff;border-radius:28px;overflow:hidden;box-shadow:0 16px 38px rgba(96,166,31,0.18);">
            <tr>
              <td style="background:linear-gradient(135deg,#FBA685 0%,#F65368 48%,#BFE97B 100%);padding:38px 28px;text-align:center;">
                <div style="font-size:30px;line-height:36px;font-weight:700;color:#ffffff;">SelfEra</div>
                <div style="margin-top:8px;font-size:15px;color:#ffffff;opacity:.95;">Confirm your email address</div>
              </td>
            </tr>
            <tr>
              <td style="padding:34px 30px 12px;text-align:center;">
                <div style="font-size:20px;font-weight:700;color:#3D5A1E;">Your verification code</div>
                <div style="margin:20px auto 18px;padding:18px 22px;display:inline-block;border-radius:22px;background:#ECEDDF;color:#60A61F;font-size:34px;font-weight:800;letter-spacing:8px;">
                  {code}
                </div>
                <div style="font-size:15px;line-height:24px;color:#5F7D3B;">
                  Enter this 6-digit code in the app to finish creating your account.
                  The code is valid for 10 minutes.
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:20px 30px 34px;text-align:center;">
                <div style="border-top:1px solid #E3DAB7;padding-top:18px;font-size:12px;line-height:18px;color:#B4BD9A;">
                  If you did not request this, you can safely ignore this email.
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def _send_verification_email(email, code):
    if not settings.EMAIL_HOST or not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        raise RuntimeError('Email SMTP is not configured on the server.')

    text_body = (
        f'Your BeautyApp verification code is {code}. '
        'Enter it in the app to finish registration. The code is valid for 10 minutes.'
    )
    message = EmailMultiAlternatives(
        subject='BeautyApp verification code',
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    message.attach_alternative(_verification_email_html(code), 'text/html')
    message.send(fail_silently=False)


def _verify_registration_code(email, code):
    verification = EmailVerificationCode.objects.filter(email=email.lower()).first()
    if verification is None:
        return False, 'Verification code was not requested for this email.'
    if verification.is_expired():
        verification.delete()
        return False, 'Verification code has expired. Please request a new one.'
    if verification.attempts >= 5:
        verification.delete()
        return False, 'Too many incorrect attempts. Please request a new code.'

    expected_hash = _hash_verification_code(email, code)
    if verification.code_hash != expected_hash:
        verification.attempts += 1
        verification.save(update_fields=['attempts', 'updated_at'])
        return False, 'Invalid verification code.'

    return True, ''


# ── Register ──────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def send_verification_code(request):
    """
    Validate registration data and send a 6-digit email verification code.
    """
    serializer = SendVerificationCodeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email']
    code = f'{random.SystemRandom().randint(0, 999999):06d}'
    expires_at = timezone.now() + timedelta(minutes=10)

    try:
        _send_verification_email(email, code)
    except Exception as exc:
        return Response(
            {'error': f'Could not send verification email: {exc}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    EmailVerificationCode.objects.update_or_create(
        email=email,
        defaults={
            'code_hash': _hash_verification_code(email, code),
            'expires_at': expires_at,
            'attempts': 0,
        },
    )
    return Response(
        {'message': 'Verification code sent. Please check your email.'},
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user with email and password.

    Request body:
        email       (required)
        password    (required)
        first_name  (optional)
        last_name   (optional)
        phone_number (optional)

    Returns: user object + JWT tokens
    """
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email']
    code = serializer.validated_data['verification_code']
    code_is_valid, error_message = _verify_registration_code(email, code)
    if not code_is_valid:
        return Response({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        user = serializer.save()
        EmailVerificationCode.objects.filter(email=email).delete()

    return Response(_auth_response(user), status=status.HTTP_201_CREATED)


# ── Login ─────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login with email and password.

    Request body:
        email    (required)
        password (required)

    Returns: user object + JWT tokens
    """
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email'].lower()
    password = serializer.validated_data['password']

    try:
        user_obj = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response(
            {'error': 'Invalid email or password.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    user = authenticate(request, username=user_obj.username, password=password)
    if user is None:
        return Response(
            {'error': 'Invalid email or password.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        return Response({'error': 'Account is disabled.'}, status=status.HTTP_403_FORBIDDEN)

    return Response(_auth_response(user), status=status.HTTP_200_OK)


# ── Google OAuth ──────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):
    """
    Authenticate via Google Sign-In (mobile flow).

    The mobile app obtains a Google ID token via the Google Sign-In SDK and
    sends it here. We verify it server-side, then create or retrieve the user.

    Request body:
        id_token (required) — Google ID token string

    Returns: user object + JWT tokens
    """
    serializer = GoogleAuthSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    if not settings.GOOGLE_CLIENT_ID:
        return Response(
            {'error': 'Google OAuth is not configured on the server.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    token = serializer.validated_data['id_token']

    try:
        id_info = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        return Response({'error': f'Invalid Google token: {exc}'}, status=status.HTTP_401_UNAUTHORIZED)

    google_id = id_info['sub']
    email = id_info.get('email', '').lower()
    first_name = id_info.get('given_name', '')
    last_name = id_info.get('family_name', '')
    avatar = id_info.get('picture', '')

    if not email:
        return Response(
            {'error': 'Google account has no email address.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Try to find by google_id first, then by email
    profile = UserProfile.objects.filter(google_id=google_id).select_related('user').first()

    if profile:
        user = profile.user
    else:
        user, created = User.objects.get_or_create(
            email__iexact=email,
            defaults={
                'username': email,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            },
        )
        if created:
            user.set_unusable_password()
            user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.google_id = google_id
        if avatar:
            profile.avatar = avatar
        profile.save()
        _ensure_client_profile(user)

    return Response(_auth_response(user), status=status.HTTP_200_OK)


# ── Token Refresh ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    """
    Refresh access token using a refresh token.

    Request body:
        refresh (required) — JWT refresh token

    Returns: new access token (and new refresh token if ROTATE_REFRESH_TOKENS=True)
    """
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response({'error': 'Refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        token = RefreshToken(refresh_token)
        data = {'access': str(token.access_token)}
        if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS'):
            token.blacklist() if hasattr(token, 'blacklist') else None
            new_refresh = RefreshToken.for_user(token.user) if hasattr(token, 'user') else token
            data['refresh'] = str(new_refresh)
        return Response(data, status=status.HTTP_200_OK)
    except Exception as exc:
        return Response({'error': f'Invalid or expired refresh token: {exc}'}, status=status.HTTP_401_UNAUTHORIZED)


# ── Current User (me) ─────────────────────────────────────────────────────────

@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Returns the currently authenticated user's profile.
    Requires Authorization: Bearer <access_token> header.

    DELETE removes the user account (cascades to client/master profiles and related data).
    """
    if request.method == 'DELETE':
        user = request.user
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    _ensure_client_profile(request.user)

    if request.method == 'GET':
        return Response(UserSerializer(_user_with_relations(request.user)).data, status=status.HTTP_200_OK)

    serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()
    return Response(UserSerializer(_user_with_relations(user)).data, status=status.HTTP_200_OK)


# ── Promote current user to master (professional account) ─────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def become_master(request):
    """
    Promote the currently authenticated client to a master (professional) account.
    Creates an empty Master profile linked to the user if one does not already exist.
    """
    if Master.objects.filter(user=request.user).exists():
        return Response(
            {'error': 'This user already has a master profile.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    full_name = request.user.get_full_name().strip() or request.user.email
    Master.objects.create(user=request.user, name=full_name, profile_photo='')
    return Response(
        UserSerializer(_user_with_relations(request.user)).data,
        status=status.HTTP_200_OK,
    )


# ── Upload profile photo (Cloudinary) ──────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_avatar(request):
    """
    Upload a profile photo to Cloudinary and update the user's avatar.
    Accepts multipart/form-data with key "photo".
    Returns: {"url": "https://res.cloudinary.com/..."}
    """
    cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', '') or ''
    api_key = getattr(settings, 'CLOUDINARY_API_KEY', '') or ''
    api_secret = getattr(settings, 'CLOUDINARY_API_SECRET', '') or ''
    cloudinary_url = getattr(settings, 'CLOUDINARY_URL', '') or os.getenv('CLOUDINARY_URL', '')

    if not all([cloud_name, api_key, api_secret]) and not cloudinary_url:
        return Response(
            {'error': 'Cloudinary is not configured on the server.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    photo = request.FILES.get('photo')
    if not photo:
        return Response(
            {'error': 'No photo file provided. Use form field "photo".'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate file type (image/* from clients is rejected — use concrete types)
    allowed_types = ('image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/heic')
    if photo.content_type not in allowed_types:
        return Response(
            {'error': f'Invalid file type. Allowed: {", ".join(allowed_types)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if photo.size > 10 * 1024 * 1024:  # 10 MB
        return Response(
            {'error': 'File too large. Maximum size is 10 MB.'},
            status=status.HTTP_400_BAD_REQUEST,
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
            folder='avatars',
            asset_folder='avatars',
            overwrite=True,
            resource_type='image',
        )
        url = result.get('secure_url') or result.get('url', '')

        if not url:
            return Response(
                {'error': 'Cloudinary did not return a URL.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Update UserProfile.avatar
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.avatar = url
        profile.save()

        # If user is a master, also update Master.profile_photo (same Cloudinary URL).
        try:
            mp = request.user.master_profile
            mp.profile_photo = url
            mp.save(update_fields=['profile_photo'])
        except Master.DoesNotExist:
            pass

        return Response({'url': url}, status=status.HTTP_200_OK)

    except Exception as exc:
        return Response(
            {'error': f'Upload failed: {str(exc)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ── All users list ────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def users_list(request):
    """
    GET /api/users/
    Returns all registered users from the database as JSON.
    """
    users = User.objects.select_related('profile', 'master_profile', 'client_profile').all().order_by('id')
    return Response(UserSerializer(users, many=True).data, status=status.HTTP_200_OK)


# ── Clients ───────────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def clients_list(request):
    """
    GET  /api/clients/  — Returns all clients from the database.
    POST /api/clients/  — Creates a new client profile.

    Only name and email are required. All appearance fields are optional
    and can be filled in later via the appearance analysis feature.

    POST body example (minimal):
    {
        "name": "Ольга Мельник",
        "email": "olga@example.com"
    }

    POST body example (full):
    {
        "name": "Ольга Мельник",
        "email": "olga@example.com",
        "phone_number": "+380991234567",
        "location": "Київ",
        "age": 28,
        "height_sm": 165,
        "eyes_color": "зелені",
        "skin_color": "світла",
        "hair_color": "русявий",
        "face_shape": "овал",
        "eye_shape": "мигдалеподібні",
        "lips_fullness": "середні",
        "brow_thickness": "середні"
    }
    """
    if request.method == 'GET':
        clients = Client.objects.all().order_by('id')
        serializer = ClientSerializer(clients, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'POST':
        serializer = ClientSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        client = serializer.save()
        return Response(ClientSerializer(client).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def my_client_profile(request):
    """
    GET   /api/clients/me/  — Returns the client profile of the logged-in user.
    PATCH /api/clients/me/  — Updates appearance fields on the logged-in user's profile.

    Requires: Authorization: Bearer <access_token>
    """
    try:
        client = request.user.client_profile
    except Client.DoesNotExist:
        return Response({'error': 'No client profile found for this user.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(ClientSerializer(client).data, status=status.HTTP_200_OK)

    if request.method == 'PATCH':
        serializer = ClientSerializer(client, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


# ── Favorite masters (authenticated) ──────────────────────────────────────────


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def favorite_masters_list(request):
    """
    GET /api/auth/favorite-masters/
    Returns favorited masters for the current user (newest first).
    """
    favs = FavoriteMaster.objects.filter(user=request.user).select_related('master', 'master__user').order_by(
        '-created_at',
    )
    masters = [f.master for f in favs if f.master.is_active]
    return Response(MasterPublicCardSerializer(masters, many=True).data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def favorite_masters_toggle(request):
    """
    POST /api/auth/favorite-masters/toggle/
    Body: { \"master_id\": <int> }
    Response: { \"is_favorite\": true|false }
    """
    ser = FavoriteToggleSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    master_id = ser.validated_data['master_id']
    try:
        master = Master.objects.get(pk=master_id, is_active=True)
    except Master.DoesNotExist:
        return Response({'detail': 'Master not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        fav = FavoriteMaster.objects.get(user=request.user, master=master)
    except FavoriteMaster.DoesNotExist:
        FavoriteMaster.objects.create(user=request.user, master=master)
        return Response({'is_favorite': True}, status=status.HTTP_200_OK)
    fav.delete()
    return Response({'is_favorite': False}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def favorite_masters_delete(request, master_id):
    """DELETE /api/auth/favorite-masters/<master_id>/ — remove from favorites."""
    FavoriteMaster.objects.filter(user=request.user, master_id=master_id).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── Moderation (staff only) ────────────────────────────────────────────────────


def _require_staff(request):
    if not request.user.is_staff:
        return Response({'detail': 'Staff access required.'}, status=status.HTTP_403_FORBIDDEN)
    return None


def _users_have_conversation(user_a, user_b):
    from chat.models import Conversation

    return (
        Conversation.objects
        .filter(participants=user_a)
        .filter(participants=user_b)
        .exists()
    )


def _master_can_report_client(master_user, client_user):
    from bookings.models import Booking

    try:
        master = master_user.master_profile
    except Master.DoesNotExist:
        return False

    return Booking.objects.filter(master=master, client=client_user).exists()


def _send_profile_report_message_to_moderator(report):
    from .report_notifications import notify_staff_by_dm

    text_body = report.text.strip()
    if not text_body:
        return

    reason_label = dict(UserReport.REASON_CHOICES).get(report.reason, report.reason)
    target_name = report.target.get_full_name().strip() or report.target.email or report.target.username
    full_msg = (
        f'[Profile report]\n'
        f'Target: {target_name}\n'
        f'Target email: {report.target.email}\n'
        f'Reason: {reason_label}\n\n'
        f'{text_body}'
    )
    notify_staff_by_dm(report.reporter, full_msg)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_user(request, user_id):
    """POST /api/users/<id>/report/ — report a user/master profile."""
    if user_id == request.user.id:
        return Response({'detail': 'You cannot report your own profile.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        target = User.objects.select_related('master_profile').get(pk=user_id)
    except User.DoesNotExist:
        return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    target_is_master = hasattr(target, 'master_profile')
    reporter_is_master = hasattr(request.user, 'master_profile')

    # Clients may report masters from the public master profile. For all other
    # profile reports, require an existing booking or chat relationship.
    allowed = target_is_master or _users_have_conversation(request.user, target)
    if reporter_is_master and not target_is_master:
        allowed = allowed or _master_can_report_client(request.user, target)

    if not allowed:
        return Response(
            {'detail': 'You can report only profiles you have interacted with.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    ser = UserReportSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        report = UserReport.objects.create(
            target=target,
            reporter=request.user,
            reason=ser.validated_data['reason'],
            text=ser.validated_data.get('text', ''),
        )
    except Exception:
        return Response({'detail': 'You have already reported this profile.'}, status=status.HTTP_409_CONFLICT)

    _send_profile_report_message_to_moderator(report)
    return Response({'detail': 'Report submitted.'}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def moderation_users(request):
    """GET /api/moderation/users/?q=... — list all users (staff only)."""
    err = _require_staff(request)
    if err:
        return err
    q = request.GET.get('q', '').strip()
    qs = (
        User.objects
        .select_related('profile', 'master_profile')
        .annotate(report_count_annotated=Count('profile_reports_received'))
        .order_by('-report_count_annotated', '-date_joined')
    )
    if q:
        qs = qs.filter(
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)
        )
    return Response(ModerationUserSerializer(qs, many=True).data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def moderation_user_delete(request, user_id):
    """DELETE /api/moderation/users/<id>/ — delete user (staff only, cannot delete self or other staff)."""
    err = _require_staff(request)
    if err:
        return err
    if user_id == request.user.id:
        return Response({'detail': 'Cannot delete your own account via moderation.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
    if target.is_staff:
        return Response({'detail': 'Cannot delete staff accounts.'}, status=status.HTTP_400_BAD_REQUEST)
    target.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def moderation_reviews(request):
    """GET /api/moderation/reviews/?q=... — list all reviews (staff only)."""
    err = _require_staff(request)
    if err:
        return err
    q = request.GET.get('q', '').strip()
    qs = (
        MasterReview.objects
        .select_related('author', 'master')
        .annotate(report_count_annotated=Count('reports'))
        .order_by('-report_count_annotated', '-created_at')
    )
    if q:
        qs = qs.filter(
            Q(comment__icontains=q) |
            Q(author__email__icontains=q) |
            Q(author__first_name__icontains=q) |
            Q(author__last_name__icontains=q) |
            Q(master__name__icontains=q)
        )
    return Response(ModerationReviewSerializer(qs, many=True).data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def moderation_review_delete(request, review_id):
    """DELETE /api/moderation/reviews/<id>/ — delete review (staff only)."""
    err = _require_staff(request)
    if err:
        return err
    try:
        review = MasterReview.objects.select_related('master').get(pk=review_id)
    except MasterReview.DoesNotExist:
        return Response({'detail': 'Review not found.'}, status=status.HTTP_404_NOT_FOUND)
    master = review.master
    review.delete()
    Master.sync_review_aggregates_for_master_id(master.pk)
    return Response(status=status.HTTP_204_NO_CONTENT)

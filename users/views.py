from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from .models import Client, UserProfile
from .serializers import (
    ClientSerializer,
    GoogleAuthSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserUpdateSerializer,
    UserSerializer,
)


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


def _auth_response(user):
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


# ── Register ──────────────────────────────────────────────────────────────────

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

    user = serializer.save()
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

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Returns the currently authenticated user's profile.
    Requires Authorization: Bearer <access_token> header.
    """
    _ensure_client_profile(request.user)

    if request.method == 'GET':
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

    serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()
    return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


# ── Upload profile photo (Cloudinary) ──────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_avatar(request):
    """
    Upload a profile photo to Cloudinary and update the user's avatar.
    Accepts multipart/form-data with key "photo".
    Returns: {"url": "https://res.cloudinary.com/..."}
    """
    cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', '')
    api_key = getattr(settings, 'CLOUDINARY_API_KEY', '')
    api_secret = getattr(settings, 'CLOUDINARY_API_SECRET', '')

    if not all([cloud_name, api_key, api_secret]):
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

    # Validate file type
    allowed_types = ('image/jpeg', 'image/png', 'image/webp', 'image/gif')
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

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
        )

        result = cloudinary.uploader.upload(
            photo,
            folder='beauty_app_profiles',
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

        # If user is a master, also update Master.profile_photo
        if hasattr(request.user, 'master_profile'):
            request.user.master_profile.profile_photo = url
            request.user.master_profile.save()

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
    users = User.objects.select_related('profile').all().order_by('id')
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

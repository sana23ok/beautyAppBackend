import logging
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Conversation, ConversationHiddenForUser, Message
from .serializers import (
    ConversationDetailSerializer,
    ConversationListSerializer,
    MessageSerializer,
    SendMessageSerializer,
    StartConversationSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)

# Dedicated Cloudinary directory for chat photos and videos.
CHAT_MEDIA_CLOUDINARY_FOLDER = 'beauty_app/chat_media'

IMAGE_TYPES = frozenset(
    ('image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/heic'),
)
VIDEO_TYPES = frozenset(
    ('video/mp4', 'video/quicktime', 'video/webm', 'video/3gpp'),
)


def _users_with_avatar_relations():
    """Users with profile + master loaded so ParticipantSerializer.get_avatar works."""
    return User.objects.select_related('profile', 'master_profile')


def _prefetch_conversations():
    return Conversation.objects.prefetch_related(
        Prefetch('participants', queryset=_users_with_avatar_relations()),
        'messages',
    ).distinct()


def _visible_conversations_qs(user):
    """Conversations the user participates in and has not removed only for themselves."""
    hidden_ids = ConversationHiddenForUser.objects.filter(user=user).values('conversation_id')
    return (
        _prefetch_conversations()
        .filter(participants=user)
        .exclude(pk__in=hidden_ids)
        .distinct()
    )


def _is_hidden_for_user(user, conversation_id):
    return ConversationHiddenForUser.objects.filter(
        conversation_id=conversation_id,
        user=user,
    ).exists()


def _clear_hidden_on_new_activity(conversation):
    ConversationHiddenForUser.objects.filter(conversation=conversation).delete()


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def conversations_list(request):
    """
    GET  /api/chat/conversations/  — List all conversations for current user.
    POST /api/chat/conversations/  — Start a new conversation with another user.
    """
    if request.method == 'GET':
        conversations = _visible_conversations_qs(request.user)

        serializer = ConversationListSerializer(
            conversations,
            many=True,
            context={'request': request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'POST':
        serializer = StartConversationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        participant_id = serializer.validated_data['participant_id']
        initial_message = serializer.validated_data.get('message', '')

        if participant_id == request.user.id:
            return Response(
                {'error': 'Cannot start a conversation with yourself.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            other_user = _users_with_avatar_relations().get(id=participant_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        existing = (
            _prefetch_conversations()
            .filter(participants=request.user)
            .filter(participants=other_user)
            .first()
        )

        if existing:
            _clear_hidden_on_new_activity(existing)
            if initial_message:
                Message.objects.create(
                    conversation=existing,
                    sender=request.user,
                    text=initial_message,
                )
                existing.save()
            return Response(
                ConversationDetailSerializer(existing, context={'request': request}).data,
                status=status.HTTP_200_OK,
            )

        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, other_user)

        if initial_message:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                text=initial_message,
            )
            _clear_hidden_on_new_activity(conversation)

        conversation = _prefetch_conversations().get(pk=conversation.pk)
        return Response(
            ConversationDetailSerializer(conversation, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_detail(request, pk):
    """
    GET /api/chat/conversations/<id>/  — Get conversation with all messages.
    """
    try:
        conversation = _prefetch_conversations().get(
            pk=pk, participants=request.user
        )
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    if _is_hidden_for_user(request.user, pk):
        return Response(
            {'error': 'Conversation not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    serializer = ConversationDetailSerializer(conversation, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def conversation_messages(request, pk):
    """
    GET  /api/chat/conversations/<id>/messages/  — Get messages in a conversation.
    POST /api/chat/conversations/<id>/messages/  — Send a new message.
    """
    try:
        conversation = Conversation.objects.get(pk=pk, participants=request.user)
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == 'GET':
        if _is_hidden_for_user(request.user, pk):
            return Response(
                {'error': 'Conversation not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        messages = conversation.messages.all()
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'POST':
        serializer = SendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            message_type=serializer.validated_data['message_type'],
            text=serializer.validated_data['text'],
            media_url=serializer.validated_data.get('media_url', ''),
        )
        conversation.save()
        _clear_hidden_on_new_activity(conversation)

        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_total(request):
    """
    GET /api/chat/unread_total/  — Total count of unread messages across all conversations.
    """
    total = Message.objects.filter(
        conversation__participants=request.user,
        is_read=False,
    ).exclude(
        sender=request.user,
    ).exclude(
        conversation_id__in=ConversationHiddenForUser.objects.filter(
            user=request.user,
        ).values('conversation_id'),
    ).count()

    return Response({'unread_total': total}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_messages_read(request, pk):
    """
    POST /api/chat/conversations/<id>/read/  — Mark all messages as read.
    """
    try:
        conversation = Conversation.objects.get(pk=pk, participants=request.user)
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    if _is_hidden_for_user(request.user, pk):
        return Response(
            {'error': 'Conversation not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    count = conversation.messages.filter(
        is_read=False
    ).exclude(
        sender=request.user
    ).update(is_read=True)

    return Response({'marked_read': count}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conversation_delete_action(request, pk):
    """
    POST /api/chat/conversations/<id>/delete/
    Body: {"scope": "self"} hides the chat only for current user.
          {"scope": "both"} deletes the conversation and messages for both users.
    """
    try:
        conversation = Conversation.objects.get(pk=pk, participants=request.user)
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    scope = (request.data.get('scope') or 'self').strip().lower()
    if scope not in ('self', 'both'):
        return Response(
            {'error': 'scope must be "self" or "both".'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if scope == 'both':
        conversation.delete()
    else:
        ConversationHiddenForUser.objects.get_or_create(
            conversation=conversation,
            user=request.user,
        )

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conversation_upload_media(request, pk):
    """
    POST /api/chat/conversations/<id>/media/
    multipart/form-data: field "file" — image or short video.

    Uploads to Cloudinary under beauty_app/chat_media/.

    Response: {"url": "<secure_url>", "message_type": "image"|"video"}
    """
    try:
        conversation = Conversation.objects.get(pk=pk, participants=request.user)
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    if _is_hidden_for_user(request.user, pk):
        return Response(
            {'error': 'Conversation not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    upload = request.FILES.get('file')
    if not upload:
        return Response(
            {'error': 'No file provided. Use form field "file".'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ctype = (upload.content_type or '').strip()
    if ctype in IMAGE_TYPES:
        resource_type = 'image'
        message_type = Message.MESSAGE_IMAGE
        max_size = 15 * 1024 * 1024
        err_size = '15 MB'
    elif ctype in VIDEO_TYPES:
        resource_type = 'video'
        message_type = Message.MESSAGE_VIDEO
        max_size = 80 * 1024 * 1024
        err_size = '80 MB'
    else:
        allowed = sorted(IMAGE_TYPES | VIDEO_TYPES)
        return Response(
            {'error': f'Unsupported type. Allowed MIME types include: {", ".join(allowed)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if upload.size > max_size:
        return Response(
            {'error': f'File too large. Maximum size for this type is {err_size}.'},
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
            upload,
            folder=CHAT_MEDIA_CLOUDINARY_FOLDER,
            asset_folder=CHAT_MEDIA_CLOUDINARY_FOLDER,
            resource_type=resource_type,
        )
        url = result.get('secure_url') or result.get('url', '')
        if not url:
            return Response(
                {'error': 'Cloudinary did not return a URL.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as exc:
        logger.exception('Failed to upload chat media to Cloudinary')
        return Response(
            {'error': f'Upload failed: {exc}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response({'url': url, 'message_type': message_type}, status=status.HTTP_201_CREATED)

from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Conversation, Message
from .serializers import (
    ConversationDetailSerializer,
    ConversationListSerializer,
    MessageSerializer,
    SendMessageSerializer,
    StartConversationSerializer,
)

User = get_user_model()


def _users_with_avatar_relations():
    """Users with profile + master loaded so ParticipantSerializer.get_avatar works."""
    return User.objects.select_related('profile', 'master_profile')


def _prefetch_conversations():
    return Conversation.objects.prefetch_related(
        Prefetch('participants', queryset=_users_with_avatar_relations()),
        'messages',
    ).distinct()


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def conversations_list(request):
    """
    GET  /api/chat/conversations/  — List all conversations for current user.
    POST /api/chat/conversations/  — Start a new conversation with another user.
    """
    if request.method == 'GET':
        conversations = (
            _prefetch_conversations()
            .filter(participants=request.user)
            .distinct()
        )

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
            text=serializer.validated_data['text'],
        )
        conversation.save()

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
    from django.db.models import Sum, Count, Q, F
    from .models import Message

    total = Message.objects.filter(
        conversation__participants=request.user,
        is_read=False,
    ).exclude(
        sender=request.user,
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

    count = conversation.messages.filter(
        is_read=False
    ).exclude(
        sender=request.user
    ).update(is_read=True)

    return Response({'marked_read': count}, status=status.HTTP_200_OK)

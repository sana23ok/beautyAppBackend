from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from .models import Conversation, Message

User = get_user_model()


class ParticipantSerializer(serializers.ModelSerializer):
    """Minimal user info for chat participants."""
    avatar = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'avatar', 'is_online', 'display_name')

    def get_avatar(self, obj):
        # Never use hasattr() for reverse OneToOne — it still raises DoesNotExist.
        # Prefer UserProfile.avatar (set by upload_avatar); then Master.profile_photo.
        try:
            if obj.profile.avatar:
                return obj.profile.avatar
        except ObjectDoesNotExist:
            pass
        try:
            if obj.master_profile.profile_photo:
                return obj.master_profile.profile_photo
        except ObjectDoesNotExist:
            pass
        return ''

    def get_is_online(self, obj):
        return False

    def get_display_name(self, obj):
        try:
            if obj.master_profile.name:
                return obj.master_profile.name
        except ObjectDoesNotExist:
            pass
        if obj.first_name or obj.last_name:
            return f"{obj.first_name} {obj.last_name}".strip()
        return obj.username or obj.email or f"User {obj.id}"


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages."""
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    is_from_me = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ('id', 'conversation', 'sender_id', 'text', 'created_at', 'is_read', 'is_from_me')
        read_only_fields = ('id', 'sender_id', 'created_at', 'is_from_me')

    def get_is_from_me(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.sender_id == request.user.id
        return False


class ConversationListSerializer(serializers.ModelSerializer):
    """Serializer for conversation list (with last message preview)."""
    participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    last_message_time = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ('id', 'participant', 'last_message', 'last_message_time', 'unread_count', 'updated_at')

    def get_participant(self, obj):
        request = self.context.get('request')
        if request and request.user:
            other = obj.get_other_participant(request.user)
            if other:
                return ParticipantSerializer(other).data
        return None

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        return last_msg.text if last_msg else ''

    def get_last_message_time(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return last_msg.created_at.strftime('%H:%M')
        return ''

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
        return 0


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Serializer for single conversation with all messages."""
    participant = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ('id', 'participant', 'messages', 'created_at', 'updated_at')

    def get_participant(self, obj):
        request = self.context.get('request')
        if request and request.user:
            other = obj.get_other_participant(request.user)
            if other:
                return ParticipantSerializer(other).data
        return None

    def get_messages(self, obj):
        request = self.context.get('request')
        messages = obj.messages.all()
        return MessageSerializer(messages, many=True, context={'request': request}).data


class SendMessageSerializer(serializers.Serializer):
    """Serializer for sending a new message."""
    text = serializers.CharField(max_length=5000)


class StartConversationSerializer(serializers.Serializer):
    """Serializer for starting a new conversation."""
    participant_id = serializers.IntegerField()
    message = serializers.CharField(max_length=5000, required=False, allow_blank=True)

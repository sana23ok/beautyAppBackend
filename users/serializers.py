from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Client, UserProfile


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    is_master = serializers.SerializerMethodField()
    client_profile_id = serializers.SerializerMethodField()
    master_profile_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'avatar',
            'phone_number',
            'is_master',
            'client_profile_id',
            'master_profile_id',
        )

    def get_avatar(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.avatar if profile else None

    def get_phone_number(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.phone_number if profile else ''

    def get_is_master(self, obj):
        return hasattr(obj, 'master_profile')

    def get_client_profile_id(self, obj):
        return obj.client_profile.id if hasattr(obj, 'client_profile') else None

    def get_master_profile_id(self, obj):
        return obj.master_profile.id if hasattr(obj, 'master_profile') else None


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    is_master = serializers.BooleanField(required=False, default=False)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        phone_number = validated_data.pop('phone_number', '')
        is_master = validated_data.pop('is_master', False)
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        UserProfile.objects.create(user=user, phone_number=phone_number)
        # Automatically create a linked Client profile
        Client.objects.create(
            user=user,
            name=f"{validated_data.get('first_name', '')} {validated_data.get('last_name', '')}".strip()
                 or validated_data['email'],
            email=validated_data['email'],
            phone_number=phone_number,
        )
        if is_master:
            from masters.models import Master

            Master.objects.create(
                user=user,
                name=f"{validated_data.get('first_name', '')} {validated_data.get('last_name', '')}".strip()
                or validated_data['email'],
                profile_photo='',
            )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=True, help_text='Google ID token from mobile SDK')


class ClientSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(source='user', read_only=True)

    class Meta:
        model = Client
        fields = '__all__'
        extra_kwargs = {
            # Required fields (must be provided on create)
            'name':           {'required': True},
            'email':          {'required': True},
            # Everything else is optional so you can create a partial profile
            'user_name':      {'required': False, 'allow_blank': True, 'default': ''},
            'phone_number':   {'required': False, 'allow_blank': True, 'default': ''},
            'location':       {'required': False, 'allow_blank': True, 'default': ''},
            'age':            {'required': False, 'allow_null': True, 'default': None},
            'height_sm':      {'required': False, 'allow_null': True, 'default': None},
            'eyes_color':     {'required': False, 'allow_blank': True, 'default': ''},
            'skin_color':     {'required': False, 'allow_blank': True, 'default': ''},
            'hair_color':     {'required': False, 'allow_blank': True, 'default': ''},
            'face_shape':     {'required': False, 'allow_blank': True, 'default': ''},
            'eye_shape':      {'required': False, 'allow_blank': True, 'default': ''},
            'lips_fullness':  {'required': False, 'allow_blank': True, 'default': ''},
            'brow_thickness': {'required': False, 'allow_blank': True, 'default': ''},
        }


class UserUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    avatar = serializers.URLField(required=False, allow_blank=True)

    def update(self, instance, validated_data):
        profile, _ = UserProfile.objects.get_or_create(user=instance)

        if 'first_name' in validated_data:
            instance.first_name = validated_data['first_name']
        if 'last_name' in validated_data:
            instance.last_name = validated_data['last_name']
        instance.save()

        if 'phone_number' in validated_data:
            profile.phone_number = validated_data['phone_number']
        if 'avatar' in validated_data:
            profile.avatar = validated_data['avatar'] or None
        profile.save()

        client, _ = Client.objects.get_or_create(
            user=instance,
            defaults={
                'name': instance.get_full_name().strip() or instance.email,
                'email': instance.email,
                'phone_number': profile.phone_number,
            },
        )
        client.name = instance.get_full_name().strip() or instance.email
        client.email = instance.email
        client.phone_number = profile.phone_number
        client.save()

        return instance

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from .models import Master, MasterWorkPhoto


class MasterWorkPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterWorkPhoto
        fields = ('id', 'photo_url', 'caption', 'uploaded_at')
        read_only_fields = ('id', 'uploaded_at')


class MasterSerializer(serializers.ModelSerializer):
    """Read serializer — returns full master profile with nested work photos."""
    work_photos = MasterWorkPhotoSerializer(many=True, read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(source='user', read_only=True, allow_null=True)
    profile_photo = serializers.SerializerMethodField()

    class Meta:
        model = Master
        fields = (
            'id',
            'user_id',
            'name',
            'specialization',
            'city',
            'address',
            'experience_years',
            'description',
            'profile_photo',
            'monday_hours',
            'tuesday_hours',
            'wednesday_hours',
            'thursday_hours',
            'friday_hours',
            'saturday_hours',
            'sunday_hours',
            'rating',
            'is_active',
            'created_at',
            'work_photos',
        )
        read_only_fields = ('id', 'rating', 'created_at')

    def get_profile_photo(self, obj):
        """Master.profile_photo, or linked User's UserProfile.avatar (user may be null)."""
        if obj.profile_photo:
            return obj.profile_photo
        user = obj.user
        if user is None:
            return ''
        try:
            if user.profile.avatar:
                return user.profile.avatar
        except ObjectDoesNotExist:
            pass
        return ''


class MasterWriteSerializer(serializers.ModelSerializer):
    """Write serializer — used when creating or updating a master."""
    work_photos = MasterWorkPhotoSerializer(many=True, required=False)

    class Meta:
        model = Master
        fields = (
            'name',
            'specialization',
            'city',
            'address',
            'experience_years',
            'description',
            'profile_photo',
            'monday_hours',
            'tuesday_hours',
            'wednesday_hours',
            'thursday_hours',
            'friday_hours',
            'saturday_hours',
            'sunday_hours',
            'work_photos',
        )

    def create(self, validated_data):
        photos_data = validated_data.pop('work_photos', [])
        master = Master.objects.create(**validated_data)
        for photo in photos_data:
            MasterWorkPhoto.objects.create(master=master, **photo)
        return master

    def update(self, instance, validated_data):
        photos_data = validated_data.pop('work_photos', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if photos_data is not None:
            instance.work_photos.all().delete()
            for photo in photos_data:
                MasterWorkPhoto.objects.create(master=instance, **photo)

        return instance

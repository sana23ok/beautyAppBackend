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

    class Meta:
        model = Master
        fields = (
            'id',
            'name',
            'specialization',
            'city',
            'address',
            'experience_years',
            'description',
            'profile_photo',
            'rating',
            'is_active',
            'created_at',
            'work_photos',
        )
        read_only_fields = ('id', 'rating', 'created_at')


class MasterCreateSerializer(serializers.ModelSerializer):
    """Write serializer — used when creating a new master via POST."""
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
            'work_photos',
        )

    def create(self, validated_data):
        photos_data = validated_data.pop('work_photos', [])
        master = Master.objects.create(**validated_data)
        for photo in photos_data:
            MasterWorkPhoto.objects.create(master=master, **photo)
        return master

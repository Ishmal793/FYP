from rest_framework import serializers
from .models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    career_profile = serializers.SerializerMethodField()
    has_career_profile = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        exclude = ('password', 'groups', 'user_permissions', 'is_superuser', 'is_staff', 'is_active')

    def get_has_career_profile(self, obj):
        return hasattr(obj, 'career_profile')

    def get_career_profile(self, obj):
        if hasattr(obj, 'career_profile'):
            return CareerProfileSerializer(obj.career_profile).data
        return None

class CareerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import CareerProfile
        model = CareerProfile
        exclude = ['vector_embedding']
        read_only_fields = ['user']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'email', 'password', 'role', 'name', 'phone', 'address', 'country',
            'date_of_birth', 'last_degree', 'current_degree', 'student_or_graduate', 'field_of_study', 'university',
            'company_name', 'company_address', 'designation'
        ]

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', 'job_seeker'),
            name=validated_data.get('name'),
            phone=validated_data.get('phone'),
            address=validated_data.get('address'),
            country=validated_data.get('country'),
            date_of_birth=validated_data.get('date_of_birth'),
            last_degree=validated_data.get('last_degree'),
            current_degree=validated_data.get('current_degree'),
            student_or_graduate=validated_data.get('student_or_graduate'),
            field_of_study=validated_data.get('field_of_study'),
            university=validated_data.get('university'),
            company_name=validated_data.get('company_name'),
            company_address=validated_data.get('company_address'),
            designation=validated_data.get('designation')
        )
        return user

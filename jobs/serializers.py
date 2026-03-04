from rest_framework import serializers
from .models import JobResult

class JobResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobResult
        fields = '__all__'
        read_only_fields = ['user', 'created_at']

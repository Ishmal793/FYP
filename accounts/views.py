from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, UserSerializer
from career_platform.orchestrator import WorkflowOrchestrator

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

class ProfileView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        return self.post(request)

from .serializers import CareerProfileSerializer

class CareerProfileView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):
        user = request.user
        data = request.data
        
        # Update Base User Fields (Personal & Detailed Education)
        if 'name' in data: user.name = data.get('name')
        if 'phone' in data: user.phone = data.get('phone')
        if 'address' in data: user.address = data.get('address')
        if 'country' in data: user.country = data.get('country')
        if 'date_of_birth' in data: user.date_of_birth = data.get('date_of_birth')
        if 'university' in data: user.university = data.get('university')
        if 'field_of_study' in data: user.field_of_study = data.get('field_of_study')
        if 'student_or_graduate' in data: user.student_or_graduate = data.get('student_or_graduate')
        user.save()

        # We assume job_seeker role here
        if hasattr(user, 'career_profile'):
            serializer = CareerProfileSerializer(user.career_profile, data=data, partial=True)
        else:
            serializer = CareerProfileSerializer(data=data)
            
        if serializer.is_valid():
            profile = serializer.save(user=user)
            # Sync Vector Embedding
            WorkflowOrchestrator.process_profile_update(user.id)
            return Response(serializer.data, status=200 if hasattr(user, 'career_profile') else 201)
        return Response(serializer.errors, status=400)

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsJobSeeker
from .models import JobResult
from .serializers import JobResultSerializer
from resumes.models import Resume

class JobHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def get(self, request):
        """Get the user's saved job matches History"""
        jobs = JobResult.objects.filter(user=request.user)
        serializer = JobResultSerializer(jobs, many=True)
        return Response({"saved_jobs": serializer.data})

    def post(self, request):
        """Save a new job match result"""
        resume_id = request.data.get('resume_id')
        resume_obj = None
        if resume_id:
            try:
                resume_obj = Resume.objects.get(id=resume_id, user=request.user)
            except Resume.DoesNotExist:
                pass
                
        # To avoid duplicates, check if user already saved this job title + company
        job_title = request.data.get('job_title')
        company = request.data.get('company')
        
        if JobResult.objects.filter(user=request.user, job_title=job_title, company=company).exists():
            return Response({"message": "Job match already saved in history."}, status=status.HTTP_200_OK)

        serializer = JobResultSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, resume=resume_obj)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

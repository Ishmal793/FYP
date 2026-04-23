import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsJobSeeker
from .agent import generate_job_description
from resumes.models import Resume

class GenerateJDView(APIView):
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def post(self, request, *args, **kwargs):
        target_role = request.data.get("target_role")
        location = request.data.get("location", "Remote")
        
        if not target_role:
            return Response({"error": "target_role is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        jd_data = generate_job_description(target_role, location)
        
        if "error" in jd_data:
            return Response(jd_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        return Response({"generated_jd": jd_data}, status=status.HTTP_200_OK)

class LockJDView(APIView):
    """
    Saves the user-edited/confirmed Job Description to the database and links it to the active Resume flow
    so the ATS Engine reads directly from the DB.
    """
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def post(self, request, resume_id, *args, **kwargs):
        locked_jd = request.data.get("locked_jd")
        target_role = request.data.get("target_role")
        
        if not locked_jd or not target_role:
            return Response({"error": "locked_jd and target_role are required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            resume = Resume.objects.get(id=resume_id, user=request.user)
            
            if isinstance(locked_jd, dict):
                resume.locked_jd = json.dumps(locked_jd)
            else:
                resume.locked_jd = str(locked_jd)
                
            resume.locked_target_role = target_role
            resume.save()
            
            return Response({"message": "Job Description locked successfully."}, status=status.HTTP_200_OK)
        except Resume.DoesNotExist:
            return Response({"error": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)

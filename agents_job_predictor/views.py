from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsJobSeeker
from resumes.models import Resume
from .agent import predict_job_titles

class JobPredictionView(APIView):
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def post(self, request, *args, **kwargs):
        resume_id = request.data.get('resume_id')
        
        if not resume_id:
            return Response({"error": "resume_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Verify the user owns this resume
            resume_obj = Resume.objects.get(id=resume_id, user=request.user)
            parsed_data = resume_obj.parsed_data
            
            if not parsed_data:
                return Response({"error": "This resume has no parsed data."}, status=status.HTTP_400_BAD_REQUEST)
                
            predicted_jobs = predict_job_titles(parsed_data)
            
            return Response({"jobs": predicted_jobs}, status=status.HTTP_200_OK)
            
        except Resume.DoesNotExist:
            return Response({"error": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

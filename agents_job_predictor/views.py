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
            parsed_data = resume_obj.parsed_data or {}
            target_field = request.data.get('target_field', '')
            
            if not parsed_data:
                return Response({"error": "This resume has no parsed data."}, status=status.HTTP_400_BAD_REQUEST)
                
            from .job_predictor_agent import run_job_prediction
            
            # Extract specific contexts for the agent
            skills_list = parsed_data.get('skills', [])
            experience_summary = parsed_data.get('experience', '')
            education_summary = parsed_data.get('education', '')
            projects_list = parsed_data.get('projects', [])
            
            # Run the new high-accuracy predictor
            prediction_result = run_job_prediction(
                preferred_field=target_field,
                skills_list=skills_list,
                experience_summary=experience_summary,
                education_summary=education_summary,
                projects_list=projects_list
            )
            
            return Response(prediction_result, status=status.HTTP_200_OK)
            
        except Resume.DoesNotExist:
            return Response({"error": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

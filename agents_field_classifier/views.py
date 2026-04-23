import logging
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsJobSeeker
from resumes.models import Resume

# Configure logging
logger = logging.getLogger(__name__)

# Import Agents
from .agent import predict_job_families
from .skills_agent import run_skills_extraction
from agents_job_predictor.job_predictor_agent import run_job_prediction

class FieldClassificationView(APIView):
    """
    Original view for initial field suggestions.
    """
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def post(self, request, *args, **kwargs):
        resume_id = request.data.get('resume_id')
        try:
            resume_obj = Resume.objects.get(id=resume_id, user=request.user)
            parsed_data = resume_obj.parsed_data
            
            # Predict Job Families
            job_families = predict_job_families(parsed_data)
            
            # Extract Skills
            resume_context = json.dumps(parsed_data)
            extracted_skills_data = run_skills_extraction(resume_context)
            
            return Response({
                "job_families": job_families,
                "top_skills": extracted_skills_data.get("skills", [])
            }, status=status.HTTP_200_OK)
            
        except Resume.DoesNotExist:
            return Response({"error": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"FieldClassificationView Error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CareerAnalysisView(APIView):
    """
    Orchestrates skills extraction and job title prediction in a sequential pipeline.
    """
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def post(self, request, *args, **kwargs):
        resume_id = request.data.get('resume_id')
        preferred_field = request.data.get('preferred_field')

        if not resume_id:
            logger.error("CareerAnalysisView: Missing resume_id")
            return Response({"error": "resume_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"CareerAnalysisView: Starting analysis for Resume ID {resume_id} in Field '{preferred_field}'")

        try:
            # 1. Fetch Resume
            resume_obj = Resume.objects.get(id=resume_id, user=request.user)
            parsed_data = resume_obj.parsed_data or {}
            
            # Step 1: Skills Extraction
            logger.info("CareerAnalysisView: Step 1 - Extracting Skills")
            resume_context = json.dumps(parsed_data)
            skills_result = run_skills_extraction(resume_context)
            
            skills_list = [s.get('name') for s in skills_result.get('skills', [])]
            logger.info(f"CareerAnalysisView: Successfully extracted {len(skills_list)} skills")

            # Step 2: Job Prediction
            logger.info("CareerAnalysisView: Step 2 - Predicting Job Titles")
            
            # Extract context for prediction
            experience_summary = parsed_data.get('experience', '')
            education_summary = parsed_data.get('education', '')
            projects_list = parsed_data.get('projects', [])
            
            prediction_data = run_job_prediction(
                preferred_field=preferred_field or "Software Engineering",
                skills_list=skills_list,
                experience_summary=experience_summary,
                education_summary=education_summary,
                projects_list=projects_list
            )
            
            # Extract the first prediction as requested or the whole list
            predictions = prediction_data.get('jobs', [])
            primary_prediction = predictions[0] if predictions else {
                "job_title": "Associate Specialist",
                "level": "Junior",
                "confidence": 50,
                "reason": "Fallback due to prediction processing."
            }
            
            logger.info(f"CareerAnalysisView: Successfully predicted job: {primary_prediction.get('job_title')}")

            # 3. Final Response
            return Response({
                "skills": skills_result.get('skills', []),
                "prediction": primary_prediction
            }, status=status.HTTP_200_OK)

        except Resume.DoesNotExist:
            logger.error(f"CareerAnalysisView: Resume {resume_id} not found for user {request.user}")
            return Response({"error": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"CareerAnalysisView: Pipeline Failure - {str(e)}")
            # Return fallback data to keep frontend stable (200 OK)
            return Response({
                "skills": [],
                "prediction": {
                    "job_title": "Generic Professional",
                    "level": "Entry-Level",
                    "confidence": 0,
                    "reason": f"Analysis failed: {str(e)}"
                }
            }, status=status.HTTP_200_OK)

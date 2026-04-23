import logging
import traceback
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsJobSeeker
from resumes.models import Resume
from .agent import generate_optimized_cv
from .profile_manager import run_profile_memory_manager
from accounts.models import CareerProfile

# Configure logging
logger = logging.getLogger(__name__)

class ProfileMergeView(APIView):
    """
    Intelligently merges extracted CV data with existing profile.
    """
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def post(self, request, *args, **kwargs):
        resume_id = request.data.get('resume_id')
        user_confirmed = request.data.get('user_confirmed', False)
        new_data = request.data.get('new_data', {})

        if not user_confirmed:
            return Response({"update_profile": False, "message": "User declined profile update."}, status=status.HTTP_200_OK)

        try:
            profile = CareerProfile.objects.get(user=request.user)
            # Serialize existing profile to dict for the agent
            existing_profile = {
                "skills": profile.skills or [],
                "experience": profile.experience_list or [],
                "projects": profile.projects or [],
                "education": profile.education_list or [],
                "certifications": profile.certifications or []
            }

            result = run_profile_memory_manager(existing_profile, new_data, user_confirmed)

            if result.get("update_profile"):
                merged = result.get("merged_profile", {})
                profile.skills = merged.get("skills", [])
                profile.experience_list = merged.get("experience", [])
                profile.projects = merged.get("projects", [])
                profile.education_list = merged.get("education", [])
                profile.certifications = merged.get("certifications", [])
                profile.save()

            return Response(result, status=status.HTTP_200_OK)

        except CareerProfile.DoesNotExist:
            return Response({"error": "Career profile not found."}, status=status.HTTP_404_NOT_FOUND)
            logger.error(f"ProfileMergeView Error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OptimizeCVView(APIView):
    """
    Executes the Advanced CV Optimization engine using Llama 3.3.
    """
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def post(self, request, *args, **kwargs):
        logger.info(f"[API] Advanced CV Optimization initiated by User: {request.user.email}")
        
        resume_id = request.data.get('resume_id')
        if not resume_id:
            return Response({"status": "error", "message": "resume_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            resume_obj = Resume.objects.get(id=resume_id, user=request.user)
            # Use raw resume text and JD text for the advanced engine
            # If parsed_data is preferred as source, we can serialize it to string
            import json
            resume_text = json.dumps(resume_obj.parsed_data)
            locked_jd = resume_obj.locked_jd
            gap_report = request.data.get('gap_report', '')
            
            if not resume_text or not locked_jd:
                return Response({
                    "status": "error",
                    "message": "Incomplete data for optimization."
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # Execute Single-Shot Stable Engine
            optimization_result = generate_optimized_cv(resume_obj.parsed_data, locked_jd, gap_report)
            
            return Response({
                "status": "success",
                "data": optimization_result
            }, status=status.HTTP_200_OK)

        except Resume.DoesNotExist:
            return Response({"status": "error", "message": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"[API] Fatal Optimizer Error: {str(e)}")
            logger.error(traceback.format_exc())
            # Stability Fallback
            return Response({
                "status": "success",
                "data": {
                    "optimized_cv_text": "Service temporarily unavailable. Please try again.",
                    "new_ats_score_estimate": 0,
                    "improvements_made": [{"type": "System", "change": "Critical failure fallback."}]
                }
            }, status=status.HTTP_200_OK)

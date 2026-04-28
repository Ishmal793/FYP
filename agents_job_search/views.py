from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsJobSeeker
from .agent import fetch_jobs_from_linkedin
from .light_ats import calculate_light_ats_score
from resumes.models import Resume
from .models import JobResult

class JobSearchView(APIView):
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def post(self, request, *args, **kwargs):
        titles = request.data.get('titles', [])
        location = request.data.get('location', 'Remote')
        job_type = request.data.get('job_type', 'Any')
        time_filter = request.data.get('time_filter', 'Any time')
        resume_id = request.data.get('resume_id')
        
        if not titles or not isinstance(titles, list):
            return Response({"error": "A list of predicted 'titles' is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        if not resume_id:
            return Response({"error": "resume_id is required for Light ATS scoring."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            resume = Resume.objects.get(id=resume_id, user=request.user)
        except Resume.DoesNotExist:
            return Response({"error": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)
            
        try:
            # 1. Fetch & Strict Validation (Sequential, Max 8, Fallback supported)
            fetch_result = fetch_jobs_from_linkedin(titles, location, job_type, time_filter, user=request.user, resume=resume)
            live_jobs = fetch_result.get("jobs", [])
            warning = fetch_result.get("warning")
            
            # 2. Fast Light ATS Scoring Engine
            scored_jobs = []
            
            # Get user's experience level for soft scoring
            user_level = "Mid"
            if hasattr(request.user, 'careerprofile') and request.user.careerprofile:
                user_level = request.user.careerprofile.experience_level
                
            for job in live_jobs:
                ats_result = calculate_light_ats_score(resume.parsed_data, job, user_experience_level=user_level)
                scored_jobs.append(ats_result)
                
            # 3. Sort by highest score and limit to Top 5
            scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)
            top_jobs = scored_jobs[:5]
            
            # 4. Database Persistence & Frontend Data Prep
            frontend_jobs = []
            for job in top_jobs:
                orig_job = next((j for j in live_jobs if j["apply_link"] == job["apply_link"]), {})
                desc = orig_job.get("description", "")
                
                db_job, created = JobResult.objects.update_or_create(
                    apply_link=job["apply_link"],
                    defaults={
                        "user": request.user,
                        "resume": resume,
                        "title": job["title"],
                        "company": job["company"],
                        "location": job["location"],
                        "description": desc,
                        "match_score": job["match_score"],
                        "missing_skills": job["missing_skills"],
                        "required_skills": job["required_skills"]
                    }
                )
                
                job_dict = job.copy()
                job_dict["description"] = desc
                job_dict["is_valid_description"] = orig_job.get("is_valid_description", False)
                job_dict["is_saved"] = db_job.is_saved
                frontend_jobs.append(job_dict)
            
            return Response({
                "live_jobs": frontend_jobs,
                "warning": warning
            }, status=status.HTTP_200_OK)
            
        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# MarketAnalysisView removed in favor of integrated Skill Analysis module.

class ToggleSaveJobView(APIView):
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def post(self, request, *args, **kwargs):
        apply_link = request.data.get('apply_link')
        if not apply_link:
            return Response({"error": "apply_link required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            job = JobResult.objects.get(apply_link=apply_link, user=request.user)
            job.is_saved = not job.is_saved
            job.save()
            return Response({"is_saved": job.is_saved}, status=status.HTTP_200_OK)
        except JobResult.DoesNotExist:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

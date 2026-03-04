from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsJobSeeker
from resumes.models import Resume
from jobs.models import JobResult
from .agent import calculate_ats_match

class ATSMatcherBatchView(APIView):
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def post(self, request, *args, **kwargs):
        resume_id = request.data.get('resume_id')
        jobs = request.data.get('jobs', []) # Expects array of dicts: [{'title': x, 'description': y, ...}]
        
        if not resume_id or not jobs:
            return Response({"error": "resume_id and jobs array are required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            resume_obj = Resume.objects.get(id=resume_id, user=request.user)
            parsed_data = resume_obj.parsed_data
            
            if not parsed_data:
                return Response({"error": "This resume has no parsed data."}, status=status.HTTP_400_BAD_REQUEST)
                
            scored_jobs = []
            
            # Note: In a production environment with massive lists, this should be parallelized or queued.
            # We process them sequentially here since the validator already capped it around ~8 jobs max.
            for job in jobs:
                title = job.get('title', '')
                desc = job.get('description', '')
                
                match_results = calculate_ats_match(parsed_data, title, desc)
                
                # Merge original job data with match results
                scored_job = {**job, **match_results}
                
                # Rule: Only include jobs with an ATS score >= 70
                if scored_job.get('ats_score', 0) >= 70:
                    scored_jobs.append(scored_job)
                    
            # Rule: Sort by highest score, return top 3
            scored_jobs.sort(key=lambda x: x.get('ats_score', 0), reverse=True)
            top_3_jobs = scored_jobs[:3]
            
            # Auto-save successful matches directly to user's history
            for stored_job in top_3_jobs:
                if not JobResult.objects.filter(user=request.user, job_title=stored_job.get('title'), company=stored_job.get('company')).exists():
                    JobResult.objects.create(
                        user=request.user,
                        resume=resume_obj,
                        job_title=stored_job.get('title', 'Unknown Title'),
                        company=stored_job.get('company', 'Unknown Company'),
                        location=stored_job.get('location', ''),
                        description=stored_job.get('description', ''),
                        job_url=stored_job.get('url', ''),
                        ats_score=stored_job.get('ats_score', 0),
                        skills_score=stored_job.get('breakdown', {}).get('skills_score', 0),
                        experience_score=stored_job.get('breakdown', {}).get('experience_score', 0),
                        education_score=stored_job.get('breakdown', {}).get('education_score', 0),
                        matching_reason=stored_job.get('matching_reason', ''),
                        improvement_suggestion=stored_job.get('improvement_suggestion', ''),
                        missing_keywords=stored_job.get('missing_keywords', [])
                    )
            
            return Response({"matched_jobs": top_3_jobs, "total_processed": len(jobs), "total_passed": len(scored_jobs)}, status=status.HTTP_200_OK)
            
        except Resume.DoesNotExist:
            return Response({"error": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsJobSeeker
from resumes.models import Resume
from jobs.models import JobResult
from .agent import calculate_ats_match
from .optimizer import optimize_cv
import json

class CalculateLockedATSView(APIView):
    """
    Strict ATS Scoring Engine that pulls the locked_jd generated internally
    and strictly calculates the 50/20/10/20 evaluation.
    """
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def post(self, request, *args, **kwargs):
        resume_id = request.data.get('resume_id')
        
        if not resume_id:
            return Response({"error": "resume_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            resume_obj = Resume.objects.get(id=resume_id, user=request.user)
            parsed_data = resume_obj.parsed_data
            
            if not parsed_data:
                return Response({"error": "This resume has no parsed data."}, status=status.HTTP_400_BAD_REQUEST)
                
            jobs_payload = request.data.get('jobs', [])
            if jobs_payload and len(jobs_payload) > 0:
                # Dynamic Live Job Match
                job_data = jobs_payload[0]
                jd_text = job_data.get('description', '')
                locked_target_role = job_data.get('title', '')
                apply_link = job_data.get('apply_link', '')
            else:
                # Fallback to Locked JD
                locked_jd = resume_obj.locked_jd
                locked_target_role = resume_obj.locked_target_role
                if not locked_jd or not locked_target_role:
                    return Response({"error": "Job Description is not locked and no dynamic job provided."}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    jd_dict = json.loads(locked_jd)
                    jd_text = f"Title: {jd_dict.get('job_title', '')}\nSummary: {jd_dict.get('summary', '')}\nHard Skills: {', '.join(jd_dict.get('hard_skills', []))}\nSoft Skills: {', '.join(jd_dict.get('soft_skills', []))}\nResponsibilities: {', '.join(jd_dict.get('responsibilities', []))}\nQualifications: {', '.join(jd_dict.get('qualifications', []))}"
                except Exception:
                    jd_text = locked_jd
                apply_link = ""
                
            # Perform Deep Evaluation
            match_results = calculate_ats_match(parsed_data, locked_target_role, jd_text)
            
            # Update the Jobs Result Table (for UI display mapping)
            # Find or update existing run
            job_res, _ = JobResult.objects.get_or_create(
                user=request.user,
                resume=resume_obj,
                company="Baseline Evaluation",
                defaults={
                    "job_title": locked_target_role,
                    "description": jd_text,
                    "overall_score": match_results.get("overall_match_score", 0),
                    "score_breakdown": match_results.get("score_breakdown", {}),
                    "searchability": match_results.get("searchability", {}),
                    "recruiter_tips": match_results.get("recruiter_tips", [])
                }
            )
            
            # Update just in case
            job_res.job_title = locked_target_role
            job_res.description = jd_text
            job_res.overall_score = match_results.get("overall_match_score", 0)
            job_res.score_breakdown = match_results.get("score_breakdown", {})
            job_res.searchability = match_results.get("searchability", {})
            job_res.recruiter_tips = match_results.get("recruiter_tips", [])
            
            # These are the new pydantic fields. Map them to DB fields.
            job_res.details = {
                "issue_summary": match_results.get("issue_summary", {}),
                "hard_skills": match_results.get("hard_skills_comparison", []),
                "soft_skills": match_results.get("soft_skills_comparison", []),
                "content_quality": match_results.get("content_quality", {}),
                "skill_gap_summary": match_results.get("skill_gap_summary", {})
            }
            job_res.save()
            
            return Response({"match_results": match_results, "job_result_id": job_res.id}, status=status.HTTP_200_OK)
            
        except Resume.DoesNotExist:
            return Response({"error": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OptimizeCVView(APIView):
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def post(self, request, *args, **kwargs):
        resume_id = request.data.get('resume_id')
        target_job = request.data.get('target_job')
        
        if not resume_id or not target_job:
            return Response({"error": "resume_id and target_job object are required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            resume_obj = Resume.objects.get(id=resume_id, user=request.user)
            parsed_data = resume_obj.parsed_data
            
            if not parsed_data:
                return Response({"error": "This resume has no parsed data."}, status=status.HTTP_400_BAD_REQUEST)
                
            job_title = target_job.get('title', '')
            job_desc = target_job.get('description', '')
            
            optimization_result = optimize_cv(parsed_data, job_title, job_desc)
            
            if "error" in optimization_result:
                 return Response(optimization_result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                 
            return Response({"optimization": optimization_result}, status=status.HTTP_200_OK)
            
        except Resume.DoesNotExist:
            return Response({"error": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from .course_advisor import advise_courses

class SkillGapAdvisorView(APIView):
    """
    Takes the JobResult skill gap summary and Target Role, and generates
    market-accurate Coursera/Udemy recommendations using Gemini.
    """
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def post(self, request, *args, **kwargs):
        resume_id = request.data.get('resume_id')
        
        if not resume_id:
            return Response({"error": "resume_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            resume_obj = Resume.objects.get(id=resume_id, user=request.user)
            target_role = resume_obj.locked_target_role
            
            # Fetch the latest JobResult for this resume to snag the skill_gap_summary
            job_res = JobResult.objects.filter(user=request.user, resume=resume_obj).order_by('-created_at').first()
            if not job_res:
                return Response({"error": "No ATS Match Report found. Please run ATS mapping first."}, status=status.HTTP_400_BAD_REQUEST)
                
            details = job_res.details or {}
            skill_gap_summary = details.get("skill_gap_summary", {})
            career_field = resume_obj.user.userprofile.target_industry if hasattr(resume_obj.user, 'userprofile') else "Technology"
            
            # Run the Gemini Advisor
            advisor_results = advise_courses(skill_gap_summary, target_role, career_field)
            
            if "error" in advisor_results:
                 return Response(advisor_results, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                 
            # Optionally cache these recommended courses into details
            details["course_recommendations"] = advisor_results.get("courses", [])
            job_res.details = details
            job_res.save()
                 
            return Response({"advisor_results": advisor_results}, status=status.HTTP_200_OK)
            
        except Resume.DoesNotExist:
            return Response({"error": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


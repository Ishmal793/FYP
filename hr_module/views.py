from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.models import CareerProfile, CustomUser
from resumes.models import Resume
from accounts.permissions import IsHR
from vector_engine.embedding_service import generate_embedding
from agents_ats_matcher.agent import calculate_ats_match
import numpy as np

class HRDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated, IsHR]

    def get(self, request):
        total_searchable = CareerProfile.objects.filter(is_searchable=True).count()
        return Response({
            "total_candidates": total_searchable,
            "recent_activity": "Recruiter Portal Active"
        })

class HRJobMatchView(APIView):
    """
    The Optimized Hybrid Pipeline: Domain Filtering -> FAISS -> Top 10 -> LLM Ranking
    """
    permission_classes = [IsAuthenticated, IsHR]

    def post(self, request):
        job_title = request.data.get("job_title")
        job_description = request.data.get("job_description")

        if not job_title or not job_description:
            return Response({"error": "Job title and description are required."}, status=400)

        # 1. Load Skills Dict & Detect JD Domain
        import json, os
        from fast_nlp_layer.nlp_utils import basic_nlp_parse
        skills_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents_resume_parser', 'skills_dict.json')
        try:
            with open(skills_path, 'r') as f:
                skill_dict = json.load(f)
        except:
            skill_dict = {}
        
        jd_parse = basic_nlp_parse(job_description, skill_dict)
        target_domain = jd_parse.get("detected_domain", "Unclear")
        print(f"[HR_MATCH] Target Domain: {target_domain}")

        # 2. Hybrid Search: Domain Filtering + Vector Similarity
        from vector_engine.search_service import VectorSearchService
        query_text = f"{job_title} {job_description}"
        query_embedding = generate_embedding(query_text)
        
        top_matches = VectorSearchService.find_top_candidates(
            query_embedding, 
            target_domain, 
            limit=10
        )

        # 3. Layer 2: LLM Deep Ranking (Only for Top 10)
        ranked_list = []
        for profile, sim, resume in top_matches:
            # Deep evaluation using Groq LLaMA
            ats_result = calculate_ats_match(resume.parsed_data, job_title, job_description)
            
            ranked_list.append({
                "candidate_name": profile.user.name,
                "candidate_id": profile.user.id,
                "ats_score": f"{ats_result.get('overall_match_score', 0)}%",
                "match_percentage": ats_result.get('overall_match_score', 0),
                "domain": resume.parsed_data.get("detected_domain"),
                "matched_skills": [s.get('skill_name') for s in ats_result.get('hard_skills_comparison', []) if s.get('status') == 'Match'][:5],
                "missing_skills": [s.get('skill_name') for s in ats_result.get('hard_skills_comparison', []) if s.get('status') == 'Missing'][:5],
                "ranking_reason": ats_result.get('recruiter_tips', ["High potential candidate"])[0]
            })

        # Final sort by LLM Match Score
        ranked_list.sort(key=lambda x: x["match_percentage"], reverse=True)

        return Response({
            "target_domain": target_domain,
            "ranked_candidates": ranked_list
        })

class HRCandidateDetailView(APIView):
    """
    Privacy-masked candidate details
    """
    permission_classes = [IsAuthenticated, IsHR]

    def get(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            profile = user.career_profile
            
            if not profile.is_searchable:
                return Response({"error": "Candidate has opted out of search."}, status=403)

            return Response({
                "name": user.name,
                "role": profile.target_job_role,
                "skills": profile.skills,
                "experience": profile.experience_list,
                "education": profile.education_list,
                "linkedin": profile.linkedin_url,
                # phone and address are hidden
            })
        except Exception as e:
            return Response({"error": "Candidate not found"}, status=404)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from resumes.models import Resume
from accounts.models import CareerProfile, CustomUser
from .agent import calculate_advanced_job_match
from vector_engine.embedding_service import generate_embedding
from vector_engine.index_manager import create_or_load_index, search_index
from agents_ats_matcher.agent import calculate_ats_match
import numpy as np
import json

class AdvancedJobMatchAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        resume_id = request.data.get("resume_id")
        jobs_list = request.data.get("jobs", [])

        if not resume_id or not jobs_list:
            return Response({"error": "Resume ID and a list of live jobs are required."}, status=400)

        try:
            resume = Resume.objects.get(id=resume_id, user=request.user)
            parsed_data = resume.parsed_data or {}
            
            career_profile = CareerProfile.objects.filter(user=request.user).first()
            
            prefs = {
                "target_job_role": career_profile.target_job_role if career_profile else "Any",
                "preferred_location": career_profile.preferred_locations[0] if career_profile and career_profile.preferred_locations else "Any",
                "expected_salary": "Standard" # Defaulting for now if not tracked openly
            }

            matched_jobs = calculate_advanced_job_match(parsed_data, prefs, jobs_list)

            return Response({
                "success": True,
                "matched_jobs": matched_jobs
            })

        except Resume.DoesNotExist:
            return Response({"error": "Resume not found."}, status=404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)

class RecruiterMatchView(APIView):
    """
    HR-facing view that finds candidates for a Job Description.
    Flow: FAISS Semantic Search -> Top 20 Candidates -> LLM Re-ranking.
    """
    permission_classes = [IsAuthenticated] # Should ideally be IsHR

    def post(self, request):
        if request.user.role != 'hr':
            return Response({"error": "Only recruiters can access this."}, status=403)

        job_title = request.data.get("job_title")
        job_description = request.data.get("job_description")

        if not job_title or not job_description:
            return Response({"error": "Job title and description are required."}, status=400)

        # 1. Generate embedding for the search query (Job Description)
        query_text = f"{job_title} {job_description}"
        query_embedding = generate_embedding(query_text)

        # 2. Semantic Retrieval (Layer 1.5)
        # Fetch all profiles with embeddings
        profiles = CareerProfile.objects.filter(is_searchable=True).exclude(vector_embedding__isnull=True)
        
        if not profiles.exists():
            return Response({"success": True, "ranked_candidates": [], "message": "No searchable candidates found."})

        # For FYP simplicity, we'll do a quick vector comparison in-memory 
        # since a local FAISS index file might be out of sync during testing.
        candidates_with_sim = []
        for p in profiles:
            sim = np.dot(query_embedding, p.vector_embedding) # Simple cosine similarity (unnormalized but decent)
            candidates_with_sim.append((p, sim))
        
        # Sort by similarity and take Top 20
        candidates_with_sim.sort(key=lambda x: x[1], reverse=True)
        top_20_profiles = [x[0] for x in candidates_with_sim[:20]]

        # 3. Intelligence Layer (Layer 2 - LLM Re-ranking)
        # Deeply evaluate the top 20 semantic matches
        ranked_candidates = []
        for profile in top_20_profiles:
            # Prepare data for ATS Engine
            # We use the candidate's latest resume for the deep match
            latest_resume = Resume.objects.filter(user=profile.user).order_by('-created_at').first()
            if not latest_resume:
                continue

            # CALL INTELLIGENCE LAYER (LLM)
            # This is the "Slow but Accurate" part, only done for Top 20
            match_results = calculate_ats_match(
                latest_resume.parsed_data, 
                job_title, 
                job_description
            )
            
            score = match_results.get("overall_match_score", 0)

            ranked_candidates.append({
                "id": profile.user.id,
                "name": profile.user.name,
                "score": score,
                "skills": profile.skills[:8], # Show first 8 skills
                "experience_summary": profile.experience,
                "email": profile.user.email,
                "linkedin": profile.linkedin_url,
                "ats_report": match_results.get("issue_summary", {})
            })

        # Final Sort by LLM Score (The true accuracy layer)
        ranked_candidates.sort(key=lambda x: x["score"], reverse=True)

        return Response({
            "success": True,
            "ranked_candidates": ranked_candidates,
            "metadata": {
                "total_searched": profiles.count(),
                "fast_filtered": len(top_20_profiles),
                "layer_1_sim_avg": float(np.mean([x[1] for x in candidates_with_sim[:20]])) if candidates_with_sim else 0
            }
        })

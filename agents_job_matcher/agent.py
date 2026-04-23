import os
import re
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

try:
    from sentence_transformers import SentenceTransformer
    # Load model lazily
    SBERT_MODEL = None
except ImportError:
    SBERT_MODEL = None

class JobMatchingProfile(BaseModel):
    eligibility_score: int = Field(description="Score from 0 to 100 on degree/experience eligibility")
    proficiency_score: int = Field(description="Score from 0 to 100 comparing matched skill proficiency depth")
    industry_score: int = Field(description="Score from 0 to 100 on cross-industry relevance")
    salary_score: int = Field(description="Score from 0 to 100 evaluating salary compatibility")
    location_score: int = Field(description="Score from 0 to 100 based on exact location/remote status")
    reasoning: str = Field(description="1 sentence explaining the scores briefly")

def get_matcher_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    llm = ChatGroq(
        api_key=api_key,
        model_name="llama-3.1-8b-instant",
        temperature=0.1
    )
    return llm.with_structured_output(JobMatchingProfile)

def compute_similarity(text1: str, text2: str) -> int:
    """ Computes the textual similarity score (0-100) using Sentence-BERT if available, fallback to TF-IDF """
    global SBERT_MODEL
    try:
        import sentence_transformers
        if SBERT_MODEL is None:
            SBERT_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = SBERT_MODEL.encode([text1, text2])
        sim = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        return max(0, min(100, int(sim * 100)))
    except Exception as e:
        print(f"[DEBUG - MATCHER] SBERT failed, using TF-IDF fallback: {str(e)}")
        vectorizer = TfidfVectorizer(stop_words='english')
        try:
            tfidf = vectorizer.fit_transform([text1, text2])
            sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
            return max(0, min(100, int(sim * 100)))
        except:
            return 50 # Safe fallback

def calculate_advanced_job_match(resume_data: dict, candidate_prefs: dict, jobs: List[dict]) -> List[dict]:
    """
    Evaluates Candidate against scraped Jobs using:
    - Sentence-BERT/KNN Contextual Similarity
    - 5 Core Parameters via LLM (Eligibility, Proficiency, Industry, Location, Salary) IN PARALLEL!
    """
    import asyncio
    
    # Compile resume corpus
    resume_corpus = f"""
    Title: {candidate_prefs.get('target_job_role', '')}
    Skills: {', '.join(resume_data.get('skills', []))}
    Experience: {resume_data.get('experience_raw', '')}
    Education: {resume_data.get('education_raw', '')}
    """
    
    llm = get_matcher_llm()
    
    async def evaluate_job(job):
        # 1. Base Similarity Calculation
        job_corpus = f"{job.get('title', '')} {job.get('description', '')[:500]}"
        base_sim = compute_similarity(resume_corpus, job_corpus)
        
        # 2. Extract advanced 5 logic parameters via LLM asynchronously
        prompt = f"""
        You are an advanced AI Recruitment Matcher. Compare the Candidate Profile to the Job Description.
        
        Candidate Profile:
        Target Role: {candidate_prefs.get('target_job_role', 'Any')}
        Pref Location: {candidate_prefs.get('preferred_location', 'Any')}
        Pref Salary: {candidate_prefs.get('expected_salary', 'Not specified')}
        Experience: {resume_data.get('experience_raw', 'Entry Level')[:500]}
        Skills: {', '.join(resume_data.get('skills', []))}
        
        Job Description:
        Title: {job.get('title')}
        Location: {job.get('location')}
        Description: {job.get('description')[:1000]}
        
        Evaluate the 5 crucial dimensions strictly returning exactly scores 0 to 100 based on fit.
        """
        try:
            eval_result = await llm.ainvoke(prompt)
            
            # Weighted Final Match Score
            final_score = int(
                (base_sim * 0.35) +
                (eval_result.eligibility_score * 0.20) +
                (eval_result.proficiency_score * 0.15) +
                (eval_result.industry_score * 0.10) +
                (eval_result.location_score * 0.10) +
                (eval_result.salary_score * 0.10)
            )
            
            return {
                "title": job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "url": job.get("url"),
                "final_match_score": final_score,
                "base_similarity": base_sim,
                "breakdown": {
                    "eligibility": eval_result.eligibility_score,
                    "proficiency": eval_result.proficiency_score,
                    "industry": eval_result.industry_score,
                    "location": eval_result.location_score,
                    "salary": eval_result.salary_score
                },
                "reasoning": eval_result.reasoning
            }
        except Exception as e:
            print(f"[DEBUG - MATCHER] Failed evaluating job {job.get('title')}: {str(e)}")
            return {
                "title": job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "url": job.get("url"),
                "final_match_score": base_sim,
                "base_similarity": base_sim,
                "breakdown": {"eligibility": 50, "proficiency": 50, "industry": 50, "location": 50, "salary": 50},
                "reasoning": "Could not deeply process parameters."
            }

    async def main_loop():
        return await asyncio.gather(*(evaluate_job(job) for job in jobs))
    
    # Run loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None
        
    if current_loop and current_loop.is_running():
        # If in a nested async context (like Jupyter or Uvicorn), nest it properly
        # Django runserver in sync mode will trigger the else block
        import nest_asyncio
        nest_asyncio.apply()
        matched_results = asyncio.run(main_loop())
    else:
        matched_results = asyncio.run(main_loop())

    # Sort descending based on final match score
    matched_results.sort(key=lambda x: x["final_match_score"], reverse=True)
    return matched_results

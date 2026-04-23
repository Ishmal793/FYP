import os
import copy
from pydantic import BaseModel, Field
from typing import List
from langchain_groq import ChatGroq
from .agent import calculate_ats_match

class SingleOptimizationRound(BaseModel):
    focus_area: str = Field(description="What was improved in this round")
    changes_made: List[str] = Field(description="Specific actionable additions or rephrasings made to the resume content")
    optimized_summary: str = Field(description="A highly optimized 'Professional Summary' paragraph")
    suggested_skills_to_add: List[str] = Field(description="Honest skills added that candidate likely has but missed.")

def get_single_round_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing")
    llm = ChatGroq(api_key=api_key, model_name="llama-3.3-70b-versatile", temperature=0.2)
    return llm.with_structured_output(SingleOptimizationRound)

def optimize_cv(parsed_resume: dict, job_title: str, job_description: str) -> dict:
    if not job_description or not parsed_resume:
        return {"error": "Missing resume or job description"}

    current_cv = copy.deepcopy(parsed_resume)
    
    # Initial Baseline
    try:
        initial_match = calculate_ats_match(current_cv, job_title, job_description)
    except:
        initial_match = {"ats_score": 0, "missing_keywords": []}
        
    original_score = initial_match.get("ats_score", 0)
    current_score = original_score
    missing_keywords = initial_match.get("missing_keywords", [])
    
    rounds = []
    llm = get_single_round_llm()
    
    for round_num in range(1, 4):
        prompt = f"""
        You are an expert ATS Optimizer. Improve the candidate's strictly parsed CV.
        
        Target Job Title: {job_title}
        Target Job Description:
        {job_description}
        
        Currently Missing Critical Keywords: {missing_keywords}
        
        Candidate CV (JSON):
        {current_cv}
        
        Task:
        - Integrate the missing keywords into a fully rewritten, highly optimized 'Professional Summary'.
        - Provide honest 'suggested_skills_to_add' that the candidate implies but didn't list in their skills array. Do not hallucinate fake hard-skills (e.g. Python if they only know HTML), but DO add semantic synonyms.
        """
        
        try:
            result = llm.invoke(prompt)
        except Exception as e:
            print(f"[DEBUG CV_OPTIMIZER] LLM Failed on round {round_num}: {e}")
            break
            
        current_cv['professional_summary'] = result.optimized_summary
        if result.suggested_skills_to_add:
            current_skills = current_cv.get('skills', [])
            current_cv['skills'] = list(set(current_skills + result.suggested_skills_to_add))
            
        # Re-evaluate
        try:
            new_match = calculate_ats_match(current_cv, job_title, job_description)
        except:
            break
            
        new_score = new_match.get('ats_score', 0)
        bump = new_score - current_score
        
        rounds.append({
            "round_number": round_num,
            "focus_area": result.focus_area,
            "changes_made": result.changes_made,
            "score_bump": bump if bump > 0 else 0
        })
        
        current_score = new_score
        missing_keywords = new_match.get("missing_keywords", [])
        
        if current_score >= 90 or not missing_keywords:
            print(f"[DEBUG CV_OPTIMIZER] Reached optimal score {current_score} or 0 missing keywords natively. Stopping early.")
            break
            
    return {
        "original_score_estimate": original_score,
        "final_score_estimate": current_score,
        "rounds": rounds,
        "optimized_summary": current_cv.get('professional_summary', ''),
        "missing_contact_info": []
    }

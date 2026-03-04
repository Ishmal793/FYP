import os
from pydantic import BaseModel, Field
from typing import List
from langchain_groq import ChatGroq

class MatchBreakdown(BaseModel):
    skills_score: int = Field(description="Score for skills overlap out of 40", ge=0, le=40)
    experience_score: int = Field(description="Score for semantic experience match out of 30", ge=0, le=30)
    education_score: int = Field(description="Score for education/qualification match out of 30", ge=0, le=30)

class ATSMatchResult(BaseModel):
    ats_score: int = Field(description="Total ATS Match Score out of 100", ge=0, le=100)
    breakdown: MatchBreakdown = Field(description="Sub-scores for the match")
    missing_keywords: List[str] = Field(description="List of critical skills or keywords missing from the candidate's resume for this job")
    matching_reason: str = Field(description="A brief explanation of why this score was given, highlighting strengths and weaknesses.")
    improvement_suggestion: str = Field(description="Actionable suggestion for the candidate to improve their fit for this specific role")

def get_ats_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables.")
    
    # We use llama-3.3-70b-versatile for high reasoning cross-referencing
    llm = ChatGroq(
        api_key=api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.1
    )
    return llm.with_structured_output(ATSMatchResult)

def calculate_ats_match(parsed_resume: dict, job_title: str, job_description: str) -> dict:
    """
    Intelligently cross-references a candidate's parsed resume with a specific job description to generate an ATS Score.
    """
    if not job_description or not parsed_resume:
        return {"ats_score": 0, "error": "Missing resume or job description"}

    structured_llm = get_ats_llm()
    
    prompt = f"""
    You are an expert AI Applicant Tracking System (ATS). 
    Your task is to analyze the candidate's Resume against the specific Job Listing and calculate an ATS Match Score (0-100).
    
    Evaluate based on this strict rubric:
    1. Skills Overlap (40 max): Do the candidate's skills and tools match the job requirements?
    2. Experience Match (30 max): Does their past experience semantically align with the job's tasks and responsibilities?
    3. Education/Qualifications (30 max): Do their degrees or certifications match the job's requirements?
    
    Candidate Resume Data:
    {parsed_resume}
    
    Target Job Title: {job_title}
    Target Job Description:
    {job_description}
    
    Instructions:
    - Assess the exact overlap. Penalize heavily if core requirements (like years of experience or hard skills) are missing.
    - Sum the three sub-scores to create the final `ats_score`.
    - Extract a precise list of `missing_keywords` that the job requires but the resume lacks.
    - Provide a short `matching_reason` summarizing the fit.
    - Provide a single, highly actionable `improvement_suggestion`.
    
    Output strictly matching the requested JSON schema.
    """
    
    try:
        result = structured_llm.invoke(prompt)
        print(f"[DEBUG - ATS_MATCHER] Match for '{job_title}': {result.ats_score}%")
        return result.dict()
    except Exception as e:
        print(f"[DEBUG - ATS_MATCHER] Exception during matching '{job_title}': {str(e)}")
        # Generic Fallback
        return {
            "ats_score": 0, 
            "breakdown": {"skills_score": 0, "experience_score": 0, "education_score": 0},
            "missing_keywords": [],
            "matching_reason": "Failed to process match correctly due to a system error.",
            "improvement_suggestion": "Try again later."
        }

import os
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

from typing import List

class Breakdown(BaseModel):
    skills: int = Field(description="Score for skills out of 40", ge=0, le=40)
    tools: int = Field(description="Score for tools out of 30", ge=0, le=30)
    certifications: int = Field(description="Score for certifications out of 20", ge=0, le=20)
    projects: int = Field(description="Score for projects out of 10", ge=0, le=10)

class ReadinessScore(BaseModel):
    score: int = Field(
        description="The total readiness score from 0 to 100", 
        ge=0, 
        le=100
    )
    breakdown: Breakdown = Field(description="Detailed breakdown of the score")
    weakest_area: str = Field(description="The weakest area identified (e.g., 'Tools & Platforms', 'Certifications')")
    suggestions: List[str] = Field(description="A list of 3 actionable short suggestions to improve")
    ai_feedback: str = Field(description="A brief overall summary feedback explaining the candidate's readiness")

def get_readiness_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables.")
    
    # We use llama-3.3-70b-versatile for high reasoning quality here
    llm = ChatGroq(
        api_key=api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.2
    )
    return llm.with_structured_output(ReadinessScore)

def calculate_readiness_score(parsed_resume_data: dict) -> dict:
    """
    Computes a readiness score based on parsed JSON resume data.
    """
    if not parsed_resume_data or not isinstance(parsed_resume_data, dict):
        return {"score": 0, "reason": "No resume data available to evaluate."}

    structured_llm = get_readiness_llm()
    
    prompt = f"""
    You are an expert HR Specialist and Career Coach. Evaluate the following candidate's parsed resume data 
    and output a Readiness Score out of 100 based on the following specific rubric:
    
    - Skills (40 max): Quality, variety, and depth of skills mentioned.
    - Tools (30 max): Proficiency and presence of specific industry-standard software/tools/platforms.
    - Certifications (20 max): Any professional verifications, degrees, or licenses.
    - Projects (10 max): Practical projects. Evaluate experience if specific project sections are missing.
    
    Resume Data:
    {parsed_resume_data}
    
    Read the dictionary completely. If fields like 'tools' or 'certifications' are empty, penalize accordingly. 
    Calculate the exact sub-scores according to the rubric, then sum them for the total `score`.
    Identify their `weakest_area` (e.g., "Tools & Platforms", "Certifications").
    Provide 3 concise actionable `suggestions` (e.g. "Learn Docker", "Add cloud certifications").
    Finally, provide a short `ai_feedback` summarizing their readiness.
    
    Output strictly matching the requested JSON schema.
    """
    
    print("[DEBUG - READINESS] Sending prompt to Groq LLM...")
    try:
        result = structured_llm.invoke(prompt)
        print(f"[DEBUG - READINESS] Readiness Output: Score {result.score}")
        return result.dict()
    except Exception as e:
        print(f"[DEBUG - READINESS] Exception during computation: {str(e)}")
        # Generic Fallback
        return {
            "score": 0, 
            "breakdown": {"skills": 0, "tools": 0, "certifications": 0, "projects": 0},
            "weakest_area": "Unknown",
            "suggestions": ["Upload a more detailed resume"],
            "ai_feedback": f"System error computing readiness score: {str(e)}"
        }

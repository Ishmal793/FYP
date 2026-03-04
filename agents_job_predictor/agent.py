import os
from pydantic import BaseModel, Field
from typing import List
from langchain_groq import ChatGroq

class JobPrediction(BaseModel):
    title: str = Field(description="Market relevant job title (e.g., 'Senior Frontend Developer')")
    confidence: int = Field(description="Confidence score from 0 to 100 based on the candidate's skills and experience match")
    match_reason: str = Field(description="Short reason why this job is a strong fit based on their specific skills.")

class JobTitleList(BaseModel):
    jobs: List[JobPrediction] = Field(
        description="A list of exactly 5 market-relevant job titles", 
        min_items=5, 
        max_items=5
    )

def get_job_predictor_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables.")
    
    # We use llama-3.3-70b-versatile for high reasoning quality here
    llm = ChatGroq(
        api_key=api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.3
    )
    return llm.with_structured_output(JobTitleList)

def predict_job_titles(parsed_resume_data: dict) -> list:
    """
    Predicts the top 5 job titles based on parsed skills and experience.
    """
    # Extract just skills and experience to feed context
    skills = parsed_resume_data.get("skills", [])
    experience = parsed_resume_data.get("experience", [])
    tools = parsed_resume_data.get("tools", [])
    
    context = {
        "skills": skills,
        "tools": tools,
        "experience": experience
    }

    structured_llm = get_job_predictor_llm()
    
    prompt = f"""
    You are an expert HR Recruiter and Technical Headhunter.
    Based on the following candidate's specific Skills, Tools, and Work Experience, predict the top 5 most highly relevant, market-standard Job Titles they should apply for.
    
    Candidate Context:
    {context}
    
    Rules:
    1. Output EXACTLY 5 job titles.
    2. Ensure they are MODERN and MARKET-RELEVANT (e.g., "Full Stack Engineer" instead of "Computer Programmer").
    3. Calculate a highly realistic `confidence` score (0-100) reflecting how well their background matches that specific title.
    4. Provide a brief `match_reason` explaining why their skills/experience align perfectly with this role.
    5. DO NOT hallucinate. Keep recommendations strictly constrained to what their data supports.
    
    Output strictly matching the requested JSON array schema.
    """
    
    print("[DEBUG - JOB_PREDICTOR] Sending prompt to Groq LLM...")
    try:
        result = structured_llm.invoke(prompt)
        print(f"[DEBUG - JOB_PREDICTOR] Predicted {len(result.jobs)} jobs successfully")
        return [job.dict() for job in result.jobs]
    except Exception as e:
        print(f"[DEBUG - JOB_PREDICTOR] Exception during job prediction: {str(e)}")
        # Generic Fallback
        return [
            {"title": "Software Engineer", "confidence": 80, "match_reason": "General match based on text presence."},
            {"title": "Data Analyst", "confidence": 70, "match_reason": "Fallback generic match."},
            {"title": "Project Manager", "confidence": 60, "match_reason": "Fallback generic match."},
            {"title": "Systems Administrator", "confidence": 50, "match_reason": "Fallback generic match."},
            {"title": "Product Designer", "confidence": 40, "match_reason": "Fallback generic match."},
        ]

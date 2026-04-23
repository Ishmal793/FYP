import os
from pydantic import BaseModel, Field
from typing import List
from langchain_groq import ChatGroq

class JobDescription(BaseModel):
    job_title: str = Field(description="The exact title of the role")
    summary: str = Field(description="A 2-3 sentence overview of the role and its impact.")
    hard_skills: List[str] = Field(description="Critical technical skills, tools, and frameworks required.")
    soft_skills: List[str] = Field(description="Essential soft skills (e.g. Leadership, Agile, Communication).")
    experience_level: str = Field(description="Expected experience (e.g. Junior, Mid-Level, Senior) and years.")
    responsibilities: List[str] = Field(description="4-5 realistic daily responsibilities.")
    qualifications: List[str] = Field(description="Educational or certification requirements.")

def get_jd_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables.")
    
    llm = ChatGroq(
        api_key=api_key,
        model_name="llama-3.1-8b-instant",
        temperature=0.4
    )
    return llm.with_structured_output(JobDescription)

def generate_job_description(target_role: str, user_location: str = "Remote") -> dict:
    """
    Generates a realistic Job Description for ATS matching purposes based on a target role.
    """
    if not target_role:
        return {"error": "Target role is required to generate a JD."}

    structured_llm = get_jd_llm()
    
    prompt = f"""
    You are an expert Technical Recruiter writing a hyper-realistic, market-standard Job Description.
    Your goal is to output a structured Job Description that will be used by an ATS system to evaluate candidate resumes.
    
    Target Role: {target_role}
    Location Type: {user_location}
    
    Instructions:
    1. Base the skills and requirements strictly on current industry standards for this exact role.
    2. Do NOT hallucinate niche requirements; keep it standard for {target_role}.
    3. Make sure the hard skills list includes the core tech stack always associated with this role.
    4. Keep the summary professional and grounded.
    
    Fill out the structured JSON model accurately.
    """
    
    try:
        result = structured_llm.invoke(prompt)
        return result.dict()
    except Exception as e:
        print(f"[DEBUG - JD GEN] Error: {e}")
        return {"error": str(e)}

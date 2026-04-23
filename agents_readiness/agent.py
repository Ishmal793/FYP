import os
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from typing import List, Optional

class ContactInfo(BaseModel):
    email: bool = Field(description="True if email is detected")
    phone: bool = Field(description="True if phone number is detected")
    location: bool = Field(description="True if location/address is detected")

class SectionStructure(BaseModel):
    summary: bool = Field(description="True if a professional summary or objective is present")
    experience: bool = Field(description="True if work experience section is present")
    education: bool = Field(description="True if education section is present")
    projects: bool = Field(description="True if projects section is present")

class SearchabilityTitleMatch(BaseModel):
    matched: bool = Field(description="True if the target_field is explicitly found in the resume header or summary")
    score: int = Field(description="Score out of 100 for title match strength", ge=0, le=100)

class HardSkillMatch(BaseModel):
    skill: str = Field(description="Name of the required hard skill")
    resume_score: int = Field(description="Score (0-100) indicating how well this skill is represented in the resume", ge=0, le=100)
    required_score: int = Field(description="Score (0-100) indicating how critical this skill is for the target role", ge=0, le=100)

class SoftSkillMatch(BaseModel):
    skill: str = Field(description="Name of the soft skill (e.g., Leadership, Communication)")
    detected: bool = Field(description="True if explicitly or implicitly demonstrated in the resume")

class MeasurableResult(BaseModel):
    metric: str = Field(description="The context of the metric (e.g., 'Increased revenue', 'Reduced latency')")
    value: str = Field(description="The numeric achievement (e.g., '25%', '$10K', '50+ users')")

class ToneAnalysis(BaseModel):
    cliche: str = Field(description="A weak or cliché word found in the resume (e.g., 'Hardworking', 'Team player')")
    suggestion: str = Field(description="A stronger action verb alternative (e.g., 'Orchestrated', 'Spearheaded')")

class WebPresence(BaseModel):
    linkedin: bool = Field(description="True if a LinkedIn URL is detected")
    portfolio: bool = Field(description="True if a GitHub, personal website, or portfolio URL is detected")

class ExperienceAnalysis(BaseModel):
    years_total: float = Field(description="Total calculated years of professional experience")
    relevant_roles: int = Field(description="Number of past roles that perfectly match or align with the target field")
    impact_bullets: int = Field(description="Total count of bullet points containing measurable numeric results")
    gaps_detected: List[str] = Field(description="List of detected employment gaps, e.g., ['2021-2022 missing']")

class JobscanATSScore(BaseModel):
    overall_score: int = Field(description="The mathematically weighted total ATS score from 0 to 100", ge=0, le=100)
    contact_info: ContactInfo
    section_structure: SectionStructure
    searchability_title_match: SearchabilityTitleMatch
    hard_skills: List[HardSkillMatch]
    soft_skills: List[SoftSkillMatch]
    measurable_results: List[MeasurableResult]
    tone_analysis: List[ToneAnalysis]
    web_presence: WebPresence
    experience_analysis: ExperienceAnalysis

def get_readiness_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables.")
    
    # We use llama-3.1-8b-instant for fast JSON generation and extremely low latency
    llm = ChatGroq(
        api_key=api_key,
        model_name="llama-3.1-8b-instant",
        temperature=0.1 # Lowered temperature for strict deterministic JSON evaluation
    )
    return llm.with_structured_output(JobscanATSScore)

def calculate_readiness_score(parsed_resume_data: dict) -> dict:
    """
    Computes a comprehensive Jobscan-style ATS score based on parsed JSON resume data.
    """
    if not parsed_resume_data or not isinstance(parsed_resume_data, dict):
        raise ValueError("No resume data available to evaluate.")

    structured_llm = get_readiness_llm()
    target_field = parsed_resume_data.get('target_field', 'Unknown Role')
    
    prompt = f"""
    You are a professional ATS analyzer. Analyze the following resume JSON against the user's locked target field. 
    Return a strict JSON object ONLY matching the required schema.

    Instructions:
    1. Only consider the data provided in "resume_data".  
    2. Evaluate all categories objectively. Use deterministic logic where possible (regex, exact matching).  
    3. Only use LLM reasoning for: Tone Analysis, Soft Skills detection, and evaluating relevance of experience roles.  
    4. Output the JSON strictly; do not include explanations, notes, or extra text.  
    5. Weight the `overall_score` using these example weights (for guidance):  
       - Target Job Match = 25%  
       - Skills (Hard + Soft) = 35%  
       - Experience Analysis = 20%  
       - Structure & Impact (Measurable results) = 15%  
       - Contact/Web = 5%

    Here is the resume data:
    {parsed_resume_data}

    Target Field:
    "{target_field}"
    """
    
    print(f"[DEBUG - READINESS] Sending Jobscan ATS evaluation prompt targeting '{target_field}'...")
    try:
        result = structured_llm.invoke(prompt)
        print(f"[DEBUG - READINESS] ATS Output Computed: Overall Score {result.overall_score}/100")
        return result.dict()
    except Exception as e:
        print(f"[DEBUG - READINESS] Exception during computation: {str(e)}")
        # Generic Fallback matching new schema perfectly to prevent UI crashes
        return {
            "overall_score": 0,
            "contact_info": {"email": False, "phone": False, "location": False},
            "section_structure": {"summary": False, "experience": False, "education": False, "projects": False},
            "searchability_title_match": {"matched": False, "score": 0},
            "hard_skills": [],
            "soft_skills": [],
            "measurable_results": [],
            "tone_analysis": [],
            "web_presence": {"linkedin": False, "portfolio": False},
            "experience_analysis": {"years_total": 0.0, "relevant_roles": 0, "impact_bullets": 0, "gaps_detected": ["Analysis Engine Failed"]}
        }


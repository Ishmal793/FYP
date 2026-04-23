import os
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from langchain_groq import ChatGroq

class SkillSet(BaseModel):
    hard_skills: List[str] = Field(description="Strict technical skills (frameworks, tools, programming languages). Returns empty array if none.", default_factory=list)
    soft_skills: List[str] = Field(description="Non-technical skills (leadership, communication, management). Returns empty array if none.", default_factory=list)

class NormalizedResume(BaseModel):
    is_valid_resume: bool = Field(description="False if the text entirely lacks professional details or is obviously empty/corrupted.")
    cleaned_skills: SkillSet
    normalized_experience_text: str = Field(description="A clean, concise summary of all experience. If none, return 'No Experience Listed'.", default="No Experience Listed")
    years_of_experience: int = Field(description="Calculated total years of experience. Int only.", default=0)

def get_normalizer_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables.")
    
    # We use 8B for fast normalization safely
    llm = ChatGroq(
        api_key=api_key,
        model_name="llama-3.1-8b-instant",
        temperature=0.0
    )
    return llm.with_structured_output(NormalizedResume)

def normalize_skills(parsed_resume_data: dict) -> dict:
    """
    Takes raw parsed output and forces it through a strict normalization pass to guarantee schema safety.
    """
    if not parsed_resume_data:
        return {
            "is_valid_resume": False,
            "cleaned_skills": {"hard_skills": [], "soft_skills": []},
            "normalized_experience_text": "No Experience",
            "years_of_experience": 0
        }
        
    structured_llm = get_normalizer_llm()
    
    # Inject context
    skills_context = parsed_resume_data.get('skills', [])
    exp_context = parsed_resume_data.get('experience', [])
    tools_context = parsed_resume_data.get('tools', [])
    
    prompt = f"""
    You are an AI Ontology normalizer. Your job is to clean up messy resume parsed data into a strict database schema.
    
    Raw Skills: {skills_context}
    Raw Tools: {tools_context}
    Raw Experience: {exp_context}
    
    Rules:
    1. Separate skills strictly into `hard_skills` and `soft_skills`. 
    2. Remove duplicates. Remove vague words (e.g., 'fast learner').
    3. Calculate exact `years_of_experience` from the experience block. Return 0 if ambiguous.
    4. Provide a `normalized_experience_text` summarizing the work history logically.
    """
    
    try:
        result = structured_llm.invoke(prompt)
        
        # Merge back safely
        parsed_resume_data['normalized_layer'] = result.dict()
        
        # Override the potentially messy arrays
        parsed_resume_data['skills'] = result.cleaned_skills.hard_skills + result.cleaned_skills.soft_skills
        parsed_resume_data['experience_raw'] = result.normalized_experience_text
        parsed_resume_data['is_safe_to_process'] = result.is_valid_resume
        
        return parsed_resume_data
    except Exception as e:
        print(f"[DEBUG - NORMALIZER] Failure: {str(e)}")
        parsed_resume_data['is_safe_to_process'] = False
        parsed_resume_data['normalized_layer'] = {
             "hard_skills": [],
             "soft_skills": [],
             "years_of_experience": 0
        }
        return parsed_resume_data

import os
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from typing import List

class Milestone(BaseModel):
    title: str = Field(description="Title of the milestone role (e.g., 'Senior Developer', 'Tech Lead')")
    timeline: str = Field(description="Estimated timeline (e.g., '1-2 Years', '5 Years')")
    required_skills: List[str] = Field(description="Key skills to acquire to reach this milestone")

class CareerTrajectory(BaseModel):
    short_term_roles: List[Milestone] = Field(description="Immediate next roles (1-2 years)")
    long_term_roles: List[Milestone] = Field(description="Senior-level roles (3-5 years)")
    career_roadmap_summary: str = Field(description="A brief narrative explaining how to transition from short-term to long-term")

def get_career_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables.")
    
    llm = ChatGroq(
        api_key=api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.2
    )
    return llm.with_structured_output(CareerTrajectory)

def predict_career_trajectory(parsed_resume_data: dict) -> dict:
    structured_llm = get_career_llm()
    
    prompt = f"""
    You are an expert Executive Tech Career Coach. Analyze the candidate's current resume data.
    Predict the most likely NEXT job roles (1-2 years) and long-term senior goals (3-5 years).
    
    Candidate Resume Data:
    {parsed_resume_data}

    Return strict JSON mapping to the trajectory schema. Provide actionable milestones and specific skills.
    """
    
    try:
        result = structured_llm.invoke(prompt)
        return result.dict()
    except Exception as e:
        print(f"[DEBUG - CAREER] Exception: {e}")
        return {
            "short_term_roles": [],
            "long_term_roles": [],
            "career_roadmap_summary": "Analysis failed. Please update your resume and try again."
        }

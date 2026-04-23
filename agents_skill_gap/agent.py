import os
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from typing import List

class Course(BaseModel):
    skill: str = Field(description="The missing skill this course addresses")
    course_title: str = Field(description="Title of the recommended course")
    platform: str = Field(description="Platform offering the course (e.g., Coursera, Udemy, edX)")
    duration_estimate: str = Field(description="Estimated time to complete (e.g., '4 weeks', '10 hours')")

class SkillGapRoadmap(BaseModel):
    missing_skills_identified: List[str] = Field(description="List of critical skills missing from the resume for the target role")
    courses: List[Course] = Field(description="List of specific course recommendations")
    action_plan: str = Field(description="Short paragraph detailing how the candidate should approach learning these skills")

def get_gap_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables.")
    
    llm = ChatGroq(
        api_key=api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.2
    )
    return llm.with_structured_output(SkillGapRoadmap)

def generate_learning_roadmap(parsed_resume_data: dict, target_job: dict) -> dict:
    structured_llm = get_gap_llm()
    
    prompt = f"""
    You are an expert tech Career Counselor. Compare the candidate's resume data against the target job details.
    Identify missing hard skills and recommend realistic, well-known courses from platforms like Udemy, Coursera, or Pluralsight to fill those gaps.

    Candidate Resume:
    {parsed_resume_data}

    Target Job:
    Title: {target_job.get('title')}
    Description: {target_job.get('description', 'N/A')}
    Missing Keywords already flagged: {target_job.get('missing_keywords', [])}

    Return ONLY a strict JSON object mapping to the target schema.
    """
    
    try:
        result = structured_llm.invoke(prompt)
        return result.dict()
    except Exception as e:
        print(f"[DEBUG - GAP] Exception: {e}")
        return {
            "missing_skills_identified": target_job.get('missing_keywords', []),
            "courses": [],
            "action_plan": "Analysis failed. Please try again."
        }

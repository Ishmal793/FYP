import os
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

class SkillAnalysis(BaseModel):
    have: List[str] = Field(description="List of skills the user successfully possesses.")
    missing: List[str] = Field(description="Critical skills the user lacks entirely based on the Target Role.")
    improve: List[str] = Field(description="Skills user has partially but needs to level up.")

class CourseItem(BaseModel):
    skill: str = Field(description="The primary skill this course targets.")
    platform: str = Field(description="Only 'Coursera' or 'Udemy'.")
    course_title: str = Field(description="Realistic, verifiable course title on the platform.")
    course_link: Optional[str] = Field(default="", description="The programmatic search URL.")
    level: str = Field(description="'Beginner', 'Intermediate', or 'Advanced'")
    priority: str = Field(description="'High' if missing skill, 'Medium' if improve skill.")
    reason: str = Field(description="A short 1-sentence reason why this exact course is recommended.")

class AdvisorResponse(BaseModel):
    skill_analysis: SkillAnalysis
    courses: List[CourseItem]

def get_gemini_llm():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from environment variables.")
    
    # We use gemini-2.5-flash or gemini-pro. Pro is more reliable for strict struct outputs.
    # We will use gemini-2.5-flash if available, or gemini-2.0-flash.
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.2
    )
    return llm.with_structured_output(AdvisorResponse)

def advise_courses(skill_gap_summary: dict, target_role: str, career_field: str) -> dict:
    """
    Takes the gap data from ATS Match and uses Gemini to map out missing/improve skills
    and recommends specific realistic Coursera/Udemy courses.
    """
    if not skill_gap_summary:
        return {"error": "Missing skill gap summary"}

    try:
        structured_llm = get_gemini_llm()
    except Exception as e:
        print(f"[DEBUG - COURSE ADVISOR] Error Initializing Gemini: {e}")
        return {"error": str(e)}
        
    prompt = f"""
    You are an expert AI Career Coach, Skill Gap Analyzer, and Learning Advisor.
    Your task is to analyze a candidate's skill gaps and recommend high-quality Coursera or Udemy courses.
    
    Inputs:
    Target Career Field: {career_field}
    Target Job Role: {target_role}
    Detected Skill Arrays: 
    {skill_gap_summary}
    
    1. Fill out 'skill_analysis' exactly matching the arrays of 'have', 'missing', and 'improve' based on the inputs provided and your industry knowledge.
    2. Provide highly realistic COURSE RECOMMENDATIONS targeted ONLY at the 'missing' and 'improve' skills.
    3. Platform MUST BE 'Coursera' or 'Udemy'.
    4. Provide the exact course title (e.g. 'Machine Learning Specialization by Andrew Ng').
    5. Prioritize 'Missing' skills as 'High' priority, and 'Improve' skills as 'Medium' priority.
    
    Return exactly matching the structured JSON format. Ensure all strings are clean.
    """
    
    try:
        result = structured_llm.invoke(prompt)
        res_dict = result.dict()
        
        # Enforce search-based links dynamically to prevent ANY broken links
        import urllib.parse
        for course in res_dict.get("courses", []):
            platform = course.get("platform", "").lower()
            query = result = urllib.parse.quote_plus(course.get("course_title", "").strip())
            
            if "coursera" in platform:
                course["course_link"] = f"https://www.coursera.org/search?query={query}"
            elif "udemy" in platform:
                course["course_link"] = f"https://www.udemy.com/courses/search/?q={query}"
            else:
                course["course_link"] = f"https://www.google.com/search?q={query}+{platform}"
                
        return res_dict
    except Exception as e:
        print(f"[DEBUG - COURSE ADVISOR] Inference Error: {str(e)}")
        # Provide fallback if rate limits or generation fails
        return {
            "skill_analysis": {
                "have": skill_gap_summary.get("skills_you_have", []),
                "missing": skill_gap_summary.get("missing_critical_skills", []),
                "improve": skill_gap_summary.get("skills_to_improve", [])
            },
            "courses": []
        }

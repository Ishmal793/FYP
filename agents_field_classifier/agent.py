import os
from pydantic import BaseModel, Field
from typing import List
from langchain_groq import ChatGroq

class JobFamilyList(BaseModel):
    job_families: List[str] = Field(
        description="A list of exactly 5 job families/career domains suitable for the candidate", 
        min_items=5, 
        max_items=5
    )

def get_classifier_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables.")
    
    # We use llama-3.3-70b-versatile for high reasoning quality here
    llm = ChatGroq(
        api_key=api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.3
    )
    return llm.with_structured_output(JobFamilyList)

def predict_job_families(parsed_resume_data: dict) -> list:
    """
    Predicts the top 5 job families based on parsed JSON resume data.
    """
    if not parsed_resume_data or not isinstance(parsed_resume_data, dict):
        return ["Software Engineering", "Data Science", "Marketing", "Finance", "Healthcare"]

    structured_llm = get_classifier_llm()
    
    prompt = f"""
    You are an expert Career Counselor and HR Specialist.
    Analyze the following candidate's parsed resume data and predict the top 5 most suitable broad "Job Families" 
    or career domains for them. 

    For example, if the resume is about React and Django, a good job family is "Software Engineering" or "Web Development".
    If it's about Pandas and SQL, "Data Science" or "Data Analytics".
    
    Resume Data:
    {parsed_resume_data}
    
    Rules:
    1. Return EXACTLY 5 distinct job families/domains.
    2. Format them as broad, recognizable industry categories (e.g., "Software Engineering", "Digital Marketing", "HR Management").
    3. Output strictly matching the requested array schema.
    """
    
    print("[DEBUG - CLASSIFIER] Sending prompt to Groq LLM...")
    try:
        result = structured_llm.invoke(prompt)
        families = result.job_families
        print(f"[DEBUG - CLASSIFIER] Predicted families: {families}")
        
        # Fallback if LLM returns less than 5 somehow
        if not families or len(families) == 0:
            raise ValueError("LLM returned empty list")
            
        return families
    except Exception as e:
        print(f"[DEBUG - CLASSIFIER] Exception during classification: {str(e)}")
        # Generic Fallback
        return ["Software Engineering", "Data Science", "Information Technology", "Business Analysis", "Project Management"]

import os
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

class JobValidationStatus(BaseModel):
    has_title: bool = Field(description="Does the job description mention or clearly imply a specific job title?")
    has_tasks: bool = Field(description="Does the job description outline specific tasks or responsibilities?")
    has_qualifications: bool = Field(description="Does the job description state required qualifications or skills?")

def get_validator_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables.")
    
    # We use LLaMA for reliable Pydantic extraction
    llm = ChatGroq(
        api_key=api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.0
    )
    return llm.with_structured_output(JobValidationStatus)

def validate_job_description(job_title: str, job_description: str) -> bool:
    """
    Checks if a job description is valid based on:
    - has_title
    - has_tasks
    - has_qualifications
    Requires at least 2 of these to be true.
    """
    if not job_description or len(job_description) < 20:
        return False

    structured_llm = get_validator_llm()
    
    prompt = f"""
    You are an expert HR Auditor. Analyze the following Job Listing and determine if it contains the necessary standard sections:
    1. Job Title (is it clear what the role is?)
    2. Tasks/Responsibilities (what will the person do?)
    3. Qualifications/Requirements (what skills or experience are needed?)
    
    Job Title: {job_title}
    Job Description: 
    {job_description}
    
    Output strictly matching the requested JSON schema.
    """
    
    try:
        result = structured_llm.invoke(prompt)
        
        score = 0
        if result.has_title: score += 1
        if result.has_tasks: score += 1
        if result.has_qualifications: score += 1
        
        is_valid = score >= 2
        print(f"[DEBUG - JD_VALIDATOR] '{job_title}' -> Title:{result.has_title}, Tasks:{result.has_tasks}, Quals:{result.has_qualifications} | VALID: {is_valid}")
        return is_valid
        
    except Exception as e:
        print(f"[DEBUG - JD_VALIDATOR] Exception during validation: {str(e)}")
        # Fallback to True to not break the pipeline on transient errors
        return True

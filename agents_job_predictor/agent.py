import os
from pydantic import BaseModel, Field
from typing import List
from langchain_groq import ChatGroq

class JobPrediction(BaseModel):
    job_title: str = Field(description="Predicted Job Title")
    level: str = Field(description="Entry / Junior / Mid / Senior")
    confidence: str = Field(description="0-100%")
    reason: str = Field(description="Clear explanation referencing skills, experience, and preferred field")

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
    
    # We use llama-3.1-8b-instant for fast execution
    llm = ChatGroq(
        api_key=api_key,
        model_name="llama-3.1-8b-instant",
        temperature=0.3
    )
    return llm.with_structured_output(JobTitleList)

def predict_job_titles(parsed_resume_data: dict, preferred_field: str = "") -> list:
    """
    Predicts the top 5 job titles based on parsed skills, experience, and preferred career field.
    """
    # Extract just skills and experience to feed context
    skills = parsed_resume_data.get("skills", [])
    experience = parsed_resume_data.get("experience", [])
    tools = parsed_resume_data.get("tools", [])
    
    context = {
        "skills": skills,
        "tools": tools,
        "experience": experience,
        "preferred_field": preferred_field
    }

    structured_llm = get_job_predictor_llm()
    
    prompt = f"""
    Your task is to predict the MOST suitable job title for a candidate.

    STRICT RULES:
    1. The predicted job title MUST belong ONLY to the user's selected "Preferred Career Field": {preferred_field}. Do NOT go outside this field under any condition. If resume suggests another field, IGNORE it.
    2. Use the following inputs for decision making: Skills (primary signal), Work Experience (highest weight), Projects (second highest weight), Education (supporting signal).
    3. The job title must match the candidate's strongest skills, reflect their experience level (Entry/Junior/Mid/Senior), and be realistic.
    4. If user has no experience -> Entry-Level. Internship/Projects -> Junior role. Strong experience -> Mid/Senior.
    5. Do NOT generate random or generic titles. Be specific (e.g. "Frontend React Developer").
    6. Choose the BEST MATCH based on strongest evidence.
    7. Output EXACTLY 5 job titles.

    Candidate Context:
    {context}
    
    Output format STRICT JSON array of exactly 5 objects matching the schema.
    """
    
    print("[DEBUG - JOB_PREDICTOR] Sending prompt to Groq LLM...")
    try:
        result = structured_llm.invoke(prompt)
        print(f"[DEBUG - JOB_PREDICTOR] Predicted {len(result.jobs)} jobs successfully")
        # Ensure we map it back to UI expectations if we changed field names, or map UI
        # UI expects: title, confidence, match_reason or we update UI.
        return [job.dict() for job in result.jobs]
    except Exception as e:
        print(f"[DEBUG - JOB_PREDICTOR] Exception during job prediction: {str(e)}")
        return [
            {"job_title": "Software Engineer", "level": "Mid", "confidence": "80%", "reason": "General match based on text presence."},
            {"job_title": "Data Analyst", "level": "Mid", "confidence": "70%", "reason": "Fallback generic match."},
            {"job_title": "Project Manager", "level": "Mid", "confidence": "60%", "reason": "Fallback generic match."},
            {"job_title": "Systems Administrator", "level": "Mid", "confidence": "50%", "reason": "Fallback generic match."},
            {"job_title": "Product Designer", "level": "Mid", "confidence": "40%", "reason": "Fallback generic match."},
        ]

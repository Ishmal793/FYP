import os
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_groq import ChatGroq

class ExperienceItem(BaseModel):
    title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    duration: str = Field(description="Duration of employment")
    description: str = Field(description="Brief summary of responsibilities")

class ExperienceItem(BaseModel):
    title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    duration: str = Field(description="Duration of employment")
    description: str = Field(description="Brief summary of responsibilities")

class EducationItem(BaseModel):
    degree: str = Field(description="Degree name")
    institution: str = Field(description="Institution name")
    year: str = Field(description="Year of graduation")

class SkillItem(BaseModel):
    name: str = Field(description="Skill Name")
    level: str = Field(description="Beginner / Intermediate / Advanced")
    reason: str = Field(description="Short explanation based on resume")

class ParsedResume(BaseModel):
    name: Optional[str] = Field(description="Full name of the candidate", default="")
    email: Optional[str] = Field(description="Email address of the candidate", default="")
    phone: Optional[str] = Field(description="Phone number of the candidate", default="")
    linkedin: Optional[str] = Field(description="LinkedIn profile URL", default="")
    portfolio: Optional[str] = Field(description="Portfolio or personal website URL", default="")
    skills: List[SkillItem] = Field(description="Top 5 most relevant professional skills", default=[])
    experience: List[ExperienceItem] = Field(description="List of work experiences", default=[])
    education: List[EducationItem] = Field(description="List of educational qualifications", default=[])
    projects: List[str] = Field(description="List of notable projects", default=[])
    tools: List[str] = Field(description="List of software, tools, and platforms used", default=[])
    certifications: List[str] = Field(description="List of professional certifications", default=[])

def get_parser_llm():
    # Make sure GROQ_API_KEY is available in the environment
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables.")
    # Initialize the Groq model
    llm = ChatGroq(
        api_key=api_key,
        model_name="llama-3.1-8b-instant",  # Fast and effective LLaMA model on Groq
        temperature=0.0
    )
    return llm.with_structured_output(ParsedResume)

def parse_resume_text(text: str) -> dict:
    """
    Parses resume text using Groq LLaMA model and returns structured JSON.
    Includes guardrail checks.
    """
    # Guardrail: Check length
    cleaned_text = text.strip()
    
    print(f"[DEBUG - PARSER] Extracted text length: {len(cleaned_text)} characters")
    if len(cleaned_text) > 0:
        print(f"[DEBUG - PARSER] Text preview: {cleaned_text[:200]}...")
    else:
        print("[DEBUG - PARSER] Text is totally empty.")
        
    if len(cleaned_text) < 50:
        return {
            "error": "Resume text is too short or could not be read. Please provide a valid resume with selectable text (not an image-only PDF)."
        }
        
    structured_llm = get_parser_llm()
    
    prompt = f"""
    You are an expert AI resume analyzer.
    Your task is to comprehensively analyze the following resume text and extract ALL relevant information into the provided JSON schema.
    
    Resume Text:
    {cleaned_text}
    
    CRITICAL INSTRUCTIONS FOR SKILL EXTRACTION:
    1. Analyze the FULL resume text carefully, including Work Experience (MOST IMPORTANT), Projects, Skills, and Education.
    2. Prioritize skills based on Frequency of mention, Depth of usage, and Real-world experience.
    3. DO NOT just copy skills blindly. Infer skills from context (e.g. built dashboard using Power BI -> include Power BI).
    4. Assign an EXPERIENCE LEVEL to each skill:
       - Beginner → basic knowledge or academic exposure
       - Intermediate → used in projects or internships
       - Advanced → used in professional work or multiple projects
    5. Output ONLY the TOP 5 most relevant skills in the `skills` array.
    6. Avoid generic skills like "MS Word", "Internet Browsing" unless strongly relevant. Quality > quantity.
    
    CRITICAL INSTRUCTIONS FOR OTHER FIELDS:
    1. EXHAUSTIVE EXTRACTION: Extract experience, education, validations, certifications, etc.
    2. NO EMPTY ARRAYS: Populate arrays if data exists.
    3. INFER DETAILS for dates/descriptions.
    4. ACCURACY: DO NOT hallucinate.
    
    Output strictly according to the required schema.
    """
    
    print("[DEBUG - PARSER] Sending prompt to Groq LLM...")
    
    try:
        result = structured_llm.invoke(prompt)
        parsed_dict = result.dict()
        print(f"[DEBUG - PARSER] Successfully parsed: {parsed_dict.keys()}")
        
        # Validation layer: Check if the result is completely empty despite long text
        has_content = any([
            len(parsed_dict.get('skills', [])),
            len(parsed_dict.get('experience', [])),
            len(parsed_dict.get('education', [])),
            len(parsed_dict.get('tools', [])),
            len(parsed_dict.get('projects', [])),
            len(parsed_dict.get('certifications', [])),
            bool(parsed_dict.get('name', '')),
            bool(parsed_dict.get('email', ''))
        ])
        
        if not has_content:
            return {"error": "AI could not identify any profile data from this resume text. Please check the resume format."}
            
        return parsed_dict
        
    except Exception as e:
        print(f"[DEBUG - PARSER] Exception during LLM parsing: {str(e)}")
        # Guardrail: Fallback JSON in case of parsing failure
        return {
            "name": "",
            "email": "",
            "phone": "",
            "linkedin": "",
            "portfolio": "",
            "skills": [],
            "experience": [],
            "education": [],
            "projects": [],
            "tools": [],
            "certifications": [],
            "error_fallback": str(e)
        }

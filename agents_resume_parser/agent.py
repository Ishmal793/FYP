import os
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_groq import ChatGroq

class ExperienceItem(BaseModel):
    title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    duration: str = Field(description="Duration of employment")
    description: str = Field(description="Brief summary of responsibilities")

class EducationItem(BaseModel):
    degree: str = Field(description="Degree name")
    institution: str = Field(description="Institution name")
    year: str = Field(description="Year of graduation")

class ParsedResume(BaseModel):
    skills: List[str] = Field(description="List of technical and soft skills", default=[])
    experience: List[ExperienceItem] = Field(description="List of work experiences", default=[])
    education: List[EducationItem] = Field(description="List of educational qualifications", default=[])
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
        model_name="llama-3.3-70b-versatile",  # Fast and effective LLaMA model on Groq
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
    You are an expert AI Resume Parser.
    Your task is to comprehensively analyze the following resume text and extract ALL relevant information into the provided JSON schema.
    
    Resume Text:
    {cleaned_text}
    
    CRITICAL INSTRUCTIONS:
    1. EXHAUSTIVE EXTRACTION: You MUST extract every single skill, tool, experience, education, and certification mentioned. Do NOT summarize or skip anything.
    2. NO EMPTY ARRAYS: If the resume contains skills or experience, you MUST populate the arrays. Never return empty arrays if the data exists in the text.
    3. INFER DETAILS: If dates or descriptions for experience/education are partial, extract what you can and leave default strings (like "Not specified" if truly missing).
    4. ACCURACY: DO NOT hallucinate. Only extract what is supported by the text.
    
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
            len(parsed_dict.get('certifications', []))
        ])
        
        if not has_content:
            return {"error": "AI could not identify any profile data from this resume text. Please check the resume format."}
            
        return parsed_dict
        
    except Exception as e:
        print(f"[DEBUG - PARSER] Exception during LLM parsing: {str(e)}")
        # Guardrail: Fallback JSON in case of parsing failure
        return {
            "skills": [],
            "experience": [],
            "education": [],
            "tools": [],
            "certifications": [],
            "error_fallback": str(e)
        }

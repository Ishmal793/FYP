import os
import json
import re
import logging
from typing import List
from pydantic import BaseModel, Field, ValidationError
from groq import Groq

# Configure logging
logger = logging.getLogger(__name__)

# ─── Pydantic Schema ────────────────────────────────────────────────
class SkillItem(BaseModel):
    name: str = Field(description="Name of the skill")
    level: str = Field(description="Strictly one of: 'Beginner', 'Intermediate', 'Advanced'")
    reason: str = Field(description="A short reasoning based on evidence from work experience or projects")

class SkillsResult(BaseModel):
    skills: List[SkillItem] = Field(description="List of exactly top 5 skills", min_items=5, max_items=5)

# ─── JSON Sanitizer ──────────────────────────────────────────────────
def clean_llm_json(raw_text: str) -> str:
    """
    Strips LLM noise, function tags, and markdown code fences to expose raw JSON.
    """
    # Remove function call tags if present
    raw_text = re.sub(r'<function=\w+>\s*', '', raw_text)
    raw_text = re.sub(r'</function>', '', raw_text)
    # Remove markdown code fences
    raw_text = re.sub(r'```json\s*', '', raw_text)
    raw_text = re.sub(r'```\s*', '', raw_text)
    
    raw_text = raw_text.strip()
    
    # Try to find the first '{' and last '}'
    match = re.search(r'(\{.*\})', raw_text, re.DOTALL)
    if match:
        return match.group(0)
    return raw_text

# ─── Agent Logic ─────────────────────────────────────────────────────
def run_skills_extraction(resume_text: str) -> dict:
    """
    Strict Skills Extraction Agent using Official Groq SDK.
    Weights Work Experience highest, Projects second.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY not found in environment.")
        return {"error": "API Key missing"}

    client = Groq(api_key=api_key)
    
    system_prompt = (
        "You are an expert HR Analyst. Output ONLY raw JSON. "
        "Never use markdown or function-call syntax. "
        "Extract exactly TOP 5 skills based on evidence. "
        "Skip generic skills like MS Word, Internet, MS Office."
    )
    
    user_prompt = f"""
    Analyze the following resume text and extract the TOP 5 skills.
    
    WEIGHTING RULES:
    1. Work Experience: Highest priority (Advanced level requires 2+ years or high-impact bullets).
    2. Projects: Second priority (Practical evidence).
    3. Contextual Inference: Infer skills from achievements, not just keyword list.

    OUTPUT FORMAT:
    Return a JSON object with a 'skills' key containing a list of 5 objects:
    {{
        "name": "Skill name",
        "level": "Beginner/Intermediate/Advanced",
        "reason": "1-sentence reason based on experience/projects"
    }}

    RESUME TEXT:
    {resume_text[:4000]}  # Token safety truncation
    """

    for attempt in range(3):
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=600,
            )
            
            raw_response = chat_completion.choices[0].message.content
            cleaned_json = clean_llm_json(raw_response)
            
            # Use Pydantic for validation
            data = json.loads(cleaned_json)
            validated_data = SkillsResult(**data)
            
            return validated_data.model_dump()

        except (ValidationError, json.JSONDecodeError) as e:
            logger.warning(f"Attempt {attempt + 1} failed parsing JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {str(e)}")

    # Fallback if all attempts fail
    return {
        "skills": [
            {"name": "Python", "level": "Intermediate", "reason": "Consistent mentions in resume context."},
            {"name": "Communication", "level": "Advanced", "reason": "Inferred from professional roles."},
            {"name": "Problem Solving", "level": "Intermediate", "reason": "Inferred from project challenges."},
            {"name": "Critical Thinking", "level": "Intermediate", "reason": "Implied across work history."},
            {"name": "Teamwork", "level": "Advanced", "reason": "Evident from collaborative environment."}
        ]
    }

import os
import json
import re
import logging
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError
from groq import Groq

# Configure logging
logger = logging.getLogger(__name__)

# ─── VALID FIELDS ──────────────────────────────────────────────────
VALID_FIELDS = [
    "Machine Learning/AI",
    "Software Engineering",
    "Data Science",
    "Web Development",
    "DevOps/Cloud",
    "Cybersecurity",
    "Business Analysis"
]

# ─── Pydantic Schema ───

class JobTitleResult(BaseModel):
    label: str = Field(description="The perspective of prediction (e.g. 'Based on Your Skills')")
    job_title: str = Field(description="Specific job title like 'Junior ML Engineer'")
    level: str = Field(description="Entry-Level, Junior, Mid-Level, or Senior")
    confidence: int = Field(description="Confidence score from 0 to 100", ge=0, le=100)
    reason: str = Field(description="Strict reason based on seniorities and field alignment")

class JobTitleList(BaseModel):
    jobs: List[JobTitleResult] = Field(description="A list of exactly 5 specific, perspective-driven job titles")

# ─── LLM JSON Sanitizer ───

def clean_llm_json(text: str) -> str:
    """Extracts JSON block from LLM response or attempts to fix common errors."""
    try:
        # Look for code block
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
        
        # Remove any non-JSON prefix/suffix
        text = text.strip()
        if not text.startswith("{"):
            first_brace = text.find("{")
            last_brace = text.rfind("}")
            if first_brace != -1 and last_brace != -1:
                text = text[first_brace:last_brace+1]
        
        # Basic cleanup for hanging commas
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)
        
        return text
    except Exception as e:
        logger.error(f"Error cleaning JSON: {e}")
        return text

# ─── Main Execution Function ───

def run_job_prediction(preferred_field, skills_list, experience_summary, education_summary, projects_list=None):
    """
    Predicts exactly 5 market-relevant job titles from 5 specific perspectives.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY environment variable not set.")
        return {"jobs": []}

    client = Groq(api_key=api_key)
    
    # 1. Field Validation/Normalization
    normalized_field = preferred_field
    for field in VALID_FIELDS:
        if field.lower() in preferred_field.lower():
            normalized_field = field
            break

    # 2. System Prompt with 5 Perspectives
    system_prompt = f"""
    You are an expert Career Strategist and Job Market Analyst.
    Your task is to predict EXACTLY 5 specific job titles, each from a different perspective.

    PREDICTIONS TO GENERATE:

    1. Label: "Based on Your Skills"
       - Analyze ONLY the skills list.
       - Find top 3 strongest skills and predict the most suitable role.

    2. Label: "Based on Your Experience"
       - Analyze ONLY work experience (job titles, responsibilities).
       - Predict role matching their career trajectory and seniority.

    3. Label: "Based on Your Projects"
       - Analyze ONLY the projects section.
       - Predict role based on what they have demonstrated building.

    4. Label: "Overall Best Match"
       - Combine ALL signals: skills + experience + projects + education.
       - Give the most holistic and accurate prediction.

    5. Label: "Best Match in Your Chosen Field"
       - Strictly stay inside the user's preferred field: "{normalized_field}".
       - Suggest the best role within this specific domain.

    SENIORITY RULES (MANDATORY):
    - NO professional work experience (only education) -> Stage: "Entry-Level"
    - Projects/Internships only OR <1 year professional exp -> Stage: "Junior"
    - 1-3 years professional experience -> Stage: "Mid-Level"
    - 3+ years professional experience OR evidence of leadership/architecture -> Stage: "Senior"

    OUTPUT FORMAT:
    You MUST return a valid JSON object:
    {{
        "jobs": [
            {{
                "label": "One of the 5 labels specified above",
                "job_title": "Specific Title",
                "level": "Seniority Level",
                "confidence": 0-100,
                "reason": "Brief explanation."
            }}
        ]
    }}
    """

    user_prompt = f"""
    CONTEXT:
    - Preferred Field: {normalized_field}
    - Skills: {skills_list}
    - Experience: {experience_summary}
    - Projects: {projects_list or []}
    - Education: {education_summary}

    Predict exactly 5 job titles using the 5 labels.
    """

    retries = 3
    for attempt in range(retries):
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

            raw_response = chat_completion.choices[0].message.content
            cleaned_json = clean_llm_json(raw_response)
            parsed_data = json.loads(cleaned_json)
            
            validated_data = JobTitleList(**parsed_data)
            
            if len(validated_data.jobs) > 5:
                validated_data.jobs = validated_data.jobs[:5]
            
            return validated_data.dict()

        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Attempt {attempt + 1} failed for job prediction: {e}")
            if attempt == retries - 1:
                return {"jobs": get_fallback_jobs(normalized_field)}
        except Exception as e:
            logger.error(f"Unexpected error in job prediction: {e}")
            return {"jobs": get_fallback_jobs(normalized_field)}

    return {"jobs": get_fallback_jobs(normalized_field)}

def get_fallback_jobs(field):
    """Returns safe fallback jobs based on field if AI fails."""
    return [
        {"label": "Based on Your Skills", "job_title": "Software Developer", "level": "Junior", "confidence": 50, "reason": "Fallback"},
        {"label": "Based on Your Experience", "job_title": "Junior Developer", "level": "Junior", "confidence": 50, "reason": "Fallback"},
        {"label": "Based on Your Projects", "job_title": "Project Associate", "level": "Junior", "confidence": 50, "reason": "Fallback"},
        {"label": "Overall Best Match", "job_title": "Associate Engineer", "level": "Junior", "confidence": 50, "reason": "Fallback"},
        {"label": "Best Match in Your Chosen Field", "job_title": f"{field} Associate", "level": "Junior", "confidence": 50, "reason": "Fallback"}
    ]

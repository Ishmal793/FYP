import os
import json
import re
import logging
from typing import List
from pydantic import BaseModel, Field, ValidationError
from groq import Groq

# Configure logging
logger = logging.getLogger(__name__)

# ─── Pydantic Schema ───

class FieldPrediction(BaseModel):
    label: str = Field(description="Perspective (e.g. 'Based on Skills')")
    field_name: str = Field(description="Predicted career field")

class CareerFieldList(BaseModel):
    fields: List[FieldPrediction] = Field(description="List of exactly 5 perspective-driven career fields")

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

def predict_job_families(parsed_resume_data: dict) -> list:
    """
    Predicts exactly 5 career fields from 5 specific perspectives.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY environment variable not set.")
        return []

    client = Groq(api_key=api_key)
    
    # 1. System Prompt with 5 Perspectives
    system_prompt = """
    You are an expert Career Counselor and HR Specialist.
    Your objective is to predict EXACTLY 5 career fields for the user based on different perspectives of their profile.

    PRIORITY RULES:
    - Experience > Skills > Projects.
    - If any section is missing, fallback to "Overall Profile" signals.
    - If experience is from a different domain, use transferable skills to predict the field.
    - Fields must be realistic, industry-standard, and specific.

    PREDICTIONS TO GENERATE:

    1. Label: "Based on Skills"
       - Analyze ONLY the skills list. Predict the most suitable industry field.

    2. Label: "Based on Experience"
       - Analyze ONLY work experience (job titles, responsibilities).
       - Predict the field they are currently on a trajectory towards.

    3. Label: "Based on Projects"
       - Analyze ONLY the projects section. 
       - What field does their demonstrated practical work align with?

    4. Label: "Overall Profile"
       - Combine ALL signals: skills + experience + projects + certifications.

    5. Label: "High Confidence Overall"
       - The single most reliable field for this candidate based on all evidence.

    OUTPUT FORMAT:
    You MUST return a valid JSON object:
    {
        "fields": [
            {
                "label": "One of the 5 labels specified above",
                "field_name": "Standard Career Field Name (e.g. 'Software Engineering', 'Data Science')"
            }
        ]
    }
    """

    user_prompt = f"""
    Resume Data:
    {json.dumps(parsed_resume_data)}

    Predict exactly 5 career fields using the 5 labels.
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
            
            validated_data = CareerFieldList(**parsed_data)
            
            if len(validated_data.fields) > 5:
                validated_data.fields = validated_data.fields[:5]
            
            # Return list of objects with labels for UI
            return [f.dict() for f in validated_data.fields]

        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Attempt {attempt + 1} failed for field classification: {e}")
            if attempt == retries - 1:
                return get_fallback_fields()
        except Exception as e:
            logger.error(f"Unexpected error in field classification: {e}")
            return get_fallback_fields()

    return get_fallback_fields()

def get_fallback_fields():
    """Returns safe fallback fields if AI fails."""
    return [
        {"label": "Based on Skills", "field_name": "Software Engineering"},
        {"label": "Based on Experience", "field_name": "Information Technology"},
        {"label": "Based on Projects", "field_name": "Data Science"},
        {"label": "Overall Profile", "field_name": "Business Analysis"},
        {"label": "High Confidence Overall", "field_name": "Technology"}
    ]

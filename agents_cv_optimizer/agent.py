import json
import re
import logging
import os
import httpx
from groq import Groq
from pydantic import BaseModel, Field, ValidationError

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Groq client with robust timeouts
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
    timeout=httpx.Timeout(
        connect=10.0,
        read=45.0,
        write=10.0,
        pool=5.0
    )
)

# ─── Pydantic Schemas ────────────────────────────────────────────────
class ImprovementMade(BaseModel):
    type: str
    change: str

class CVOptimizationResult(BaseModel):
    optimized_cv_text: str
    new_ats_score_estimate: int
    improvements_made: list[ImprovementMade]
    user_action_suggestions: list[str] = Field(description="Actionable coaching tips for the user")

# ─── Data Pre-processing ─────────────────────────────────────────────
def clean_input_data(parsed_resume: dict) -> dict:
    """
    Cleanses the input resume data before AI processing.
    """
    cleaned = {}
    essential_fields = [
        'name', 'email', 'phone', 'skills', 'experience', 
        'education', 'projects', 'certifications', 'target_job_title',
        'linkedin', 'portfolio', 'tools'
    ]
    
    for field in essential_fields:
        val = parsed_resume.get(field, "")
        if field == 'skills' and isinstance(val, str):
            val = [s.strip() for s in re.split(r'[,|;]', val) if s.strip()]
        cleaned[field] = val
    return cleaned

# ─── JSON Cleaner ────────────────────────────────────────────────────
def clean_llm_json(raw: str) -> str:
    """Extract pure JSON from LLM output."""
    raw = re.sub(r'```json\s*', '', raw)
    raw = re.sub(r'```\s*', '', raw)
    raw = raw.strip()
    
    match = re.search(r'(\{.*\}|\[.*\])', raw, re.DOTALL)
    if match:
        return match.group(0).strip()
    return raw

# ─── AI Instruction Layer ────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert CV Optimization and ATS Improvement Engine.
Your task is to improve a candidate's CV ONLY using the information already present in the CV.

STRICT RULES:
1. DO NOT add new skills, tools, technologies, or experiences.
2. DO NOT invent numbers, achievements, or job responsibilities.
3. DO NOT assume anything not explicitly written in the CV.
4. NO Hallucinations. Only rephrase and restructure existing content.
5. GOAL: Make it ATS-friendly, keyword-aligned, and professionally written.
6. FORMAT: You MUST return a valid JSON object.
"""

def generate_optimized_cv(parsed_resume: dict, locked_jd: str, gap_report: str = "") -> dict:
    """
    Primary entry point for the high-precision CV optimizer.
    """
    cleaned_resume = clean_input_data(parsed_resume)
    
    prompt = f"""
    Rewrite the CV to improve ATS compatibility and job relevance.
    
    📌 INPUTS:
    1. Original CV Data: {json.dumps(cleaned_resume)}
    2. Job Description: {locked_jd}
    3. Gap Analysis Report: {gap_report}

    📌 YOUR TASK:
    - Improving wording and clarity.
    - Rephrasing existing experience using stronger professional language.
    - Aligning existing content with keywords from Job Description.
    - Highlighting relevant skills already present in CV.
    - Removing unnecessary or weak phrasing.

    📌 STRICT RULES:
    - DO NOT add any new information.
    - DO NOT hallucinate skills or experience.
    - DO NOT change facts or exaggerated achievements.
    - ONLY rephrase and restructure existing content.

    📌 OUTPUT FORMAT (Return ONLY valid JSON):
    {{
        "optimized_cv_text": "Honest, realistic, and structured CV text",
        "new_ats_score_estimate": 0-100,
        "improvements_made": [
            {{"type": "Wording", "change": "Rephrased 'worked on' to 'Spearheaded'"}}
        ],
        "user_action_suggestions": [
            "Coaching tips for the user based on the Gap Report"
        ]
    }}
    """

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2500,
                response_format={"type": "json_object"}
            )

            raw = response.choices[0].message.content
            data = json.loads(raw)
            
            # Validation
            validated = CVOptimizationResult(**data)
            return validated.model_dump()
            
        except Exception as e:
            logger.warning(f"[Optimizer] Attempt {attempt+1} failed: {str(e)}")
            if attempt == 2:
                return {
                    "optimized_cv_text": f"Strict optimization failed. Check original data.",
                    "new_ats_score_estimate": 0,
                    "improvements_made": [{"type": "System", "change": "Fallback triggered"}],
                    "user_action_suggestions": ["Manual alignment required"]
                }

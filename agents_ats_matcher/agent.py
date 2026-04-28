import os
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_groq import ChatGroq

class IssueSummary(BaseModel):
    hard_skills_issues: int = 0
    soft_skills_issues: int = 0
    searchability_issues: int = 0
    recruiter_tips_count: int = 0

class ContactInfoData(BaseModel):
    email: str = Field(description="'Present' or 'Missing'")
    phone: str = Field(description="'Present' or 'Missing'")
    address: str = Field(description="'Present' or 'Missing'")

class SearchabilityStatus(BaseModel):
    contact_info: ContactInfoData = Field(default_factory=lambda: ContactInfoData(email='Missing', phone='Missing', address='Missing'))
    summary_section: str = "Missing"
    education_heading: str = "Missing"
    experience_heading: str = "Missing"
    job_title_match: str = "Not Found"
    date_formatting: str = "Improper"
    education_match: str = "Does Not Match"

class SkillComparisonRow(BaseModel):
    skill_name: str = "Unknown"
    resume_count: int = 0
    jd_count: int = 0
    status: str = "Missing"

class SoftSkillComparisonRow(BaseModel):
    skill_name: str = "Unknown"
    resume_status: str = "Missing"
    jd_status: str = "Required"
    status: str = "Missing"

class ATSScoreBreakdown(BaseModel):
    hard_skills_score: int = 0
    soft_skills_score: int = 0
    experience_score: int = 0
    education_score: int = 0
    keyword_format_score: int = 0

class ContentQualityAnalysis(BaseModel):
    measurable_results: str = "Not Found"
    resume_tone: str = "Needs Improvement"
    web_presence: str = "Missing"
    word_count_status: str = "Too Short"

class SkillGapSummary(BaseModel):
    skills_you_have: List[str] = Field(default_factory=list)
    missing_critical_skills: List[str] = Field(default_factory=list)
    skills_to_improve: List[str] = Field(default_factory=list)

class DeepEducation(BaseModel):
    status: str = "Not Matching"
    explanation: str = "N/A"
    suggestions: List[str] = Field(default_factory=list)

class DeepExperience(BaseModel):
    status: str = "Not Matching"
    years_extracted: str = "0"
    relevance_explanation: str = "N/A"
    suggestions: List[str] = Field(default_factory=list)

class DeepQuality(BaseModel):
    measurable_results_found: bool = False
    action_verbs_strong: bool = False
    feedback: str = "N/A"

class DeepJobTitle(BaseModel):
    status: str = "Not Found"
    suggestion: str = "N/A"

class DeterministicATSResponse(BaseModel):
    overall_match_score: int = 0
    issue_summary: IssueSummary = Field(default_factory=IssueSummary)
    searchability: SearchabilityStatus = Field(default_factory=SearchabilityStatus)
    hard_skills_comparison: List[SkillComparisonRow] = Field(default_factory=list)
    soft_skills_comparison: List[SoftSkillComparisonRow] = Field(default_factory=list)
    score_breakdown: ATSScoreBreakdown = Field(default_factory=lambda: ATSScoreBreakdown(hard_skills_score=0, soft_skills_score=0, experience_score=0, education_score=0, keyword_format_score=0))
    content_quality: ContentQualityAnalysis = Field(default_factory=lambda: ContentQualityAnalysis(measurable_results='Not Found', resume_tone='Needs Improvement', web_presence='Missing', word_count_status='Too Short'))
    skill_gap_summary: SkillGapSummary = Field(default_factory=SkillGapSummary)
    recruiter_tips: List[str] = Field(default_factory=list)
    
    # New Deep Analysis Fields
    deep_education: DeepEducation = Field(default_factory=lambda: DeepEducation(status='Not Matching', explanation='Error', suggestions=[]))
    deep_experience: DeepExperience = Field(default_factory=lambda: DeepExperience(status='Not Matching', years_extracted='0', relevance_explanation='Error', suggestions=[]))
    deep_quality: DeepQuality = Field(default_factory=lambda: DeepQuality(measurable_results_found=False, action_verbs_strong=False, feedback='Error'))
    deep_job_title: DeepJobTitle = Field(default_factory=lambda: DeepJobTitle(status='Not Found', suggestion='Error'))
    deep_insights: List[str] = Field(default_factory=list)

def get_ats_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables.")
    
    llm = ChatGroq(
        api_key=api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.1
    )
    return llm.with_structured_output(DeterministicATSResponse)


def calculate_ats_match(parsed_resume: dict, job_title: str, job_description: str) -> dict:
    print(f"[DEBUG - ATS_MATCHER] Matching for '{job_title}'. Resume keys: {list(parsed_resume.keys())}")
    if not job_description or not parsed_resume:
        return {"overall_score": 0, "error": "Missing resume or job description"}

    structured_llm = get_ats_llm()
    
    prompt = f"""
    You are an AI ATS Intelligence Engine and Deep Match Analyzer (Similar to Jobscan/Resume Worded).
    
    Candidate Resume Data:
    {parsed_resume}
    
    Target Job Title: {job_title}
    Target Job Description:
    {job_description}
    
    EVALUATION RULES (STRICT ATS LOGIC):
    
    1. Scoring Weight (Max 100):
       - Hard Skills Match: 40% (If critical skills missing, score MUST drop significantly)
       - Soft Skills Match: 10%
       - Experience Match: 20%
       - Education Match: 10%
       - Keyword Density & Formatting: 20%
       
       *If the candidate lacks required hard skills or experience, the overall score MUST be below 80.*
    
    2. Deep Education & Experience Analysis (NEW):
       - deep_education: Explain why education matches or fails. Suggest improvements (e.g., 'Add relevant coursework').
       - deep_experience: Extract YOE. Compare roles. Explain relevance. Provide actionable suggestions.
       - deep_quality: Detect measurable results (numbers, %). Give specific feedback if missing.
       - deep_job_title: Detect if exact title is in resume. Suggest adding it.
       - deep_insights: Provide smart, recruiter-level insights about the candidate's profile.
    
    3. Searchability Constraints:
       - Strictly evaluate if Email, Phone, Address are Present/Missing.
       - Verify explicit Summary, Education, and Work Experience sections.
       - Determine Date Formatting accurately.
    
    4. Skills Grid & Issue Summary:
       - Analyze 'skills', 'tools', 'experience' fields.
       - You MUST populate BOTH `hard_skills_comparison` and `soft_skills_comparison` arrays.
       - `hard_skills_comparison` status -> 'Match', 'Missing', or 'Partial'.
       - `soft_skills_comparison` status -> 'Match' or 'Missing'.
    
    5. Final Skill Gap: Fill the skill_gap_summary precisely based on matched and missing critical skills.
    
    Output exactly corresponding to the JSON schema. YOU MUST INCLUDE ALL ARRAYS (hard_skills_comparison AND soft_skills_comparison). No extra text.
    """
    
    try:
        raw_result = structured_llm.invoke(prompt)
        match_results = raw_result.dict()
        
        # --- DETERMINISTIC POST-PROCESSING (Single Source of Truth) ---
        
        # 1. Hard Skills Analysis from Table
        hard_skills_table = match_results.get("hard_skills_comparison", [])
        matched_count = len([s for s in hard_skills_table if s.get("status") == "Match"])
        missing_count = len([s for s in hard_skills_table if s.get("status") == "Missing"])
        partial_count = len([s for s in hard_skills_table if s.get("status") == "Partial"])
        total_skills = len(hard_skills_table)
        
        # 2. Soft Skills Analysis from Table (SSOT Fix)
        soft_skills_table = match_results.get("soft_skills_comparison", [])
        soft_matched_count = len([s for s in soft_skills_table if s.get("status") == "Match"])
        soft_missing_count = len([s for s in soft_skills_table if s.get("status") == "Missing"])
        total_soft_skills = len(soft_skills_table)
        
        # 3. Hard Skills Score Calculation (Base on Matched + Partial credit)
        # partial matches get 50% credit
        skills_raw_match = matched_count + (partial_count * 0.5)
        skills_match_percent = (skills_raw_match / total_skills * 100) if total_skills > 0 else 0
        
        # 4. Soft Skills Score Calculation
        soft_skills_percent = (soft_matched_count / total_soft_skills * 100) if total_soft_skills > 0 else 0
        
        # 5. Validation Layer
        if match_results["issue_summary"]["hard_skills_issues"] != missing_count:
            print(f"[ERROR - ATS_VALIDATION] Hard Skill Mismatch! LLM reported {match_results['issue_summary']['hard_skills_issues']} but table has {missing_count} missing.")
            match_results["issue_summary"]["hard_skills_issues"] = missing_count

        if match_results["issue_summary"]["soft_skills_issues"] != soft_missing_count:
            print(f"[ERROR - ATS_VALIDATION] Soft Skill Mismatch! LLM reported {match_results['issue_summary']['soft_skills_issues']} but table has {soft_missing_count} missing.")
            # Enforce Single Source of Truth
            match_results["issue_summary"]["soft_skills_issues"] = soft_missing_count
            
        # 6. Strict Weighted Formula Recalculation
        # Formula: (Skills % * 0.5) + (Experience % * 0.2) + (Education % * 0.2) + (Quality % * 0.1)
        
        raw_breakdown = match_results.get("score_breakdown", {})
        
        exp_score_norm = (raw_breakdown.get("experience_score", 0) / 20 * 100)
        edu_score_norm = (raw_breakdown.get("education_score", 0) / 10 * 100)
        
        # Quality score now influenced by Soft Skills + Keyword Format
        keyword_score_norm = (raw_breakdown.get("keyword_format_score", 0) / 20 * 100)
        # 50/50 blend of soft skills and formatting for Quality
        quality_score_norm = (soft_skills_percent * 0.5) + (keyword_score_norm * 0.5)
        
        # Final Combined Score
        final_score = (
            (skills_match_percent * 0.5) + 
            (exp_score_norm * 0.2) + 
            (edu_score_norm * 0.2) + 
            (quality_score_norm * 0.1)
        )
        
        # 7. Update match_results to ensure UI shows corrected values
        match_results["overall_match_score"] = int(final_score)
        match_results["score_breakdown"]["hard_skills_score"] = int(skills_match_percent * 0.4)
        match_results["score_breakdown"]["soft_skills_score"] = int(soft_skills_percent * 0.1)
        match_results["score_breakdown"]["keyword_format_score"] = int(quality_score_norm * 0.2)
        
        # 8. Update Unified Analysis
        match_results["unified_analysis"] = {
            "skills_analysis": {
                "matched": matched_count,
                "missing": missing_count,
                "total": total_skills
            },
            "soft_skills_analysis": {
                "matched": soft_matched_count,
                "missing": soft_missing_count,
                "total": total_soft_skills
            },
            "ats_score": int(final_score),
            "breakdown": {
                "hard_skills": round(skills_match_percent, 2),
                "soft_skills": round(soft_skills_percent, 2),
                "experience": round(exp_score_norm, 2),
                "education": round(edu_score_norm, 2),
                "quality": round(quality_score_norm, 2)
            }
        }
        
        print(f"[DEBUG - ATS_MATCHER] Match Result: {match_results['overall_match_score']}% (SSOT Applied for Hard & Soft Skills)")
        return match_results

    except Exception as e:
        print(f"[DEBUG - ATS_MATCHER] Exception during matching '{job_title}': {str(e)}")
        # Fallback logic...
        return {
            "overall_match_score": 0,
            "issue_summary": {"hard_skills_issues": 1, "soft_skills_issues": 1, "searchability_issues": 1, "recruiter_tips_count": 1},
            "searchability": {
                "contact_info": {"email": "Missing", "phone": "Missing", "address": "Missing"},
                "summary_section": "Missing",
                "education_heading": "Missing",
                "experience_heading": "Missing",
                "job_title_match": "Not Found",
                "date_formatting": "Improper",
                "education_match": "Does Not Match"
            },
            "hard_skills_comparison": [],
            "soft_skills_comparison": [],
            "score_breakdown": {
                "hard_skills_score": 0, "soft_skills_score": 0, "experience_score": 0, "education_score": 0, "keyword_format_score": 0
            },
            "content_quality": {
                "measurable_results": "Not Found",
                "resume_tone": "Needs Improvement",
                "web_presence": "Missing",
                "word_count_status": "Too Short"
            },
            "skill_gap_summary": {
                "skills_you_have": [], "missing_critical_skills": [], "skills_to_improve": []
            },
            "recruiter_tips": ["Retry processing. Formatting failed."],
            "deep_education": {
                "status": "Not Matching",
                "explanation": "Could not analyze education due to an error.",
                "suggestions": ["Ensure your education section is clearly formatted."]
            },
            "deep_experience": {
                "status": "Not Matching",
                "years_extracted": "Unknown",
                "relevance_explanation": "Could not analyze experience.",
                "suggestions": ["Use standard formatting for your work history."]
            },
            "deep_quality": {
                "measurable_results_found": False,
                "action_verbs_strong": False,
                "feedback": "Could not analyze quality metrics."
            },
            "deep_job_title": {
                "status": "Not Found",
                "suggestion": "Include the exact job title in your resume."
            },
            "deep_insights": ["System error occurred. Please try again."]
        }

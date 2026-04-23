import json
import os
from langchain_groq import ChatGroq

def get_coach_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    # Reduced temperature to 0.0 for grounding and reducing hallucinations
    return ChatGroq(
        api_key=api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.0 
    )

def load_career_knowledge():
    """Load industry standard career path data."""
    kb_path = os.path.join(os.path.dirname(__file__), 'career_knowledge.json')
    try:
        with open(kb_path, 'r') as f:
            return json.load(f)
    except:
        return {}

def generate_grounded_response(user_query, context_data):
    """
    Hybrid RAG: Candidate Data + Industry Knowledge Base
    """
    llm = get_coach_llm()
    career_kb = load_career_knowledge()
    
    # Simple retrieval logic: if a target role or domain is found in context, inject relevant KB
    domain = context_data.get('detected_domain', 'IT & Software')
    industry_advice = career_kb.get(domain, career_kb.get('IT & Software', {}))
    
    prompt = f"""
    You are an Expert AI Career Coach. 
    You must provide advice grounded in BOTH the candidate's specific profile AND industry-standard career paths.
    
    --- CANDIDATE PROFILE ---
    {json.dumps(context_data, indent=2)}
    
    --- INDUSTRY STANDARD PATHS (Knowledge Base) ---
    {json.dumps(industry_advice, indent=2)}
    
    --- USER QUESTION ---
    {user_query}
    
    STRICT GUIDELINES:
    1. GROUNDING: Only suggest skills or certifications found in the Industry Standard Paths that the candidate is MISSING.
    2. NO HALLUCINATION: Do not invent experiences for the candidate.
    3. REALISM: If the candidate wants to be a "Data Scientist" but lacks "Statistics", flag this as a critical gap.
    4. ACTIONABLE: Give 3 specific, numbered steps.
    
    Provide a professional, data-backed response:
    """
    
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"The AI Coach is currently unavailable: {str(e)}"

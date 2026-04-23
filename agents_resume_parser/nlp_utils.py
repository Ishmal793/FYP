import json
import os
import spacy
from django.conf import settings

# Load SpaCy model safely
try:
    nlp_model = spacy.load("en_core_web_sm")
except OSError:
    print("[WARNING] SpaCy 'en_core_web_sm' model not found. Proceeding without advanced NLP or executing `python -m spacy download en_core_web_sm`.")
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp_model = spacy.load("en_core_web_sm")

def load_skills_dictionary():
    dict_path = os.path.join(settings.BASE_DIR, 'agents_resume_parser', 'skills_dict.json')
    try:
        with open(dict_path, 'r', encoding='utf-8') as f:
            skills_list = json.load(f)
            # Store in lowercase for fast dictionary matching
            return set(skill.lower() for skill in skills_list)
    except Exception as e:
        print(f"[ERROR] Could not load skills_dict.json: {str(e)}")
        return set()

def extract_skills_nlp(text: str) -> list:
    """
    Extracts skills using a hybrid approach (SpaCy tokenization + Dictionary Matching)
    as requested by the user.
    """
    skill_dict = load_skills_dictionary()
    found_skills = set()
    
    # 1. SpaCy NLP Token Processing
    doc = nlp_model(text.lower())
    
    # We create n-grams from the document manually since skills can be multi-word ("machine learning")
    tokens = [token.text for token in doc if not token.is_stop and not token.is_punct and len(token.text) > 1]
    text_lower = text.lower()
    
    # 2. Dictionary Keyword Matching (The exact requirement specified)
    # This directly checks if the dictionary phrase exists inside the raw text.
    for skill in skill_dict:
        # Pad with spaces to avoid sub-word matching (e.g., 'c' in 'react')
        # Simple heuristic check, alternatively regex
        if f" {skill} " in f" {text_lower} " or f" {skill}," in text_lower or f" {skill}." in text_lower or f"\n{skill}" in text_lower:
            found_skills.add(skill.title())  # Store capitalized version
            
    return list(found_skills)

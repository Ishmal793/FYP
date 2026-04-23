import spacy
import re
import json
from spacy.matcher import PhraseMatcher

# Load small SpaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except:
    import en_core_web_sm
    nlp = en_core_web_sm.load()

def extract_contact_info(text):
    """Fast extraction using Regex (No LLM)"""
    email_regex = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    phone_regex = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    
    emails = re.findall(email_regex, text)
    phones = re.findall(phone_regex, text)
    
    return {
        "email": emails[0] if emails else None,
        "phone": phones[0] if phones else None
    }

def get_skill_to_domain_map(structured_dict):
    """Flatten structured dict into skill -> domain mapping."""
    mapping = {}
    for domain, categories in structured_dict.items():
        if isinstance(categories, dict):
            for cat, skills in categories.items():
                for skill in skills:
                    mapping[skill.lower()] = domain
        elif isinstance(categories, list):
            for skill in categories:
                mapping[skill.lower()] = domain
    return mapping

def detect_domain(found_skills, mapping):
    """Detect primary domain based on skill counts."""
    if not found_skills:
        return "Unclear"
    
    domain_counts = {}
    for skill in found_skills:
        domain = mapping.get(skill.lower())
        if domain:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
    if not domain_counts:
        return "Unclear"
    
    # Get domain with max skills
    primary_domain = max(domain_counts, key=domain_counts.get)
    return primary_domain

def extract_skills_fast(text, skill_dict):
    """Fast skill extraction using SpaCy PhraseMatcher with Domain Awareness"""
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    
    # 1. Flatten all skills for initial matching
    skill_to_domain = get_skill_to_domain_map(skill_dict)
    all_skills = list(skill_to_domain.keys())
    
    patterns = [nlp.make_doc(skill) for skill in all_skills]
    matcher.add("SKILL_LIST", patterns)
    
    doc = nlp(text)
    matches = matcher(doc)
    
    found_skills = set()
    for match_id, start, end in matches:
        span = doc[start:end]
        found_skills.add(span.text.lower())
    
    # 2. Detect Domain
    detected_domain = detect_domain(found_skills, skill_to_domain)
    
    # 3. Filter skills by domain (allow 'Business & Management' for everyone as soft skills)
    if detected_domain != "Unclear":
        filtered_skills = [
            s for s in found_skills 
            if skill_to_domain.get(s) == detected_domain or skill_to_domain.get(s) == "Business & Management"
        ]
    else:
        filtered_skills = list(found_skills)
        
    return {
        "domain": detected_domain,
        "skills": filtered_skills
    }

def basic_nlp_parse(text, skill_dict):
    """Main entry point for Fast Layer 1 Parsing"""
    contact = extract_contact_info(text)
    extraction = extract_skills_fast(text, skill_dict)
    
    return {
        "detected_domain": extraction["domain"],
        "email": contact["email"],
        "phone": contact["phone"],
        "skills": extraction["skills"]
    }

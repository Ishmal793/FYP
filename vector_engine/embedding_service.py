import os
from sentence_transformers import SentenceTransformer

# Load a lightweight, high-performance model
# all-MiniLM-L6-v2 is fast and produces 384-dimensional embeddings
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    print(f"Error loading Sentence-BERT: {e}")
    model = None

def generate_embedding(text):
    """Generate a vector for the given text."""
    if not model or not text:
        return None
    return model.encode(text).tolist()

def get_document_string(parsed_data):
    """Convert parsed resume data into a single string for embedding."""
    if not parsed_data:
        return ""
    
    parts = []
    # Add skills
    skills = parsed_data.get('skills', [])
    if isinstance(skills, list):
        # Handle list of dicts or list of strings
        skill_names = [s.get('name', str(s)) if isinstance(s, dict) else str(s) for s in skills]
        parts.append(f"Skills: {', '.join(skill_names)}")
    
    # Add experience summary
    experience = parsed_data.get('experience', [])
    if isinstance(experience, list):
        exp_titles = [e.get('job_title', '') for e in experience if isinstance(e, dict)]
        parts.append(f"Experience: {', '.join(exp_titles)}")
    
    # Add education
    education = parsed_data.get('education', [])
    if isinstance(education, list):
        edu_degrees = [e.get('degree', '') for e in education if isinstance(e, dict)]
        parts.append(f"Education: {', '.join(edu_degrees)}")
        
    return " ".join(parts)

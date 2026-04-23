import re

def calculate_light_ats_score(resume_data: dict, job: dict, user_experience_level="Mid") -> dict:
    """
    Ultra-fast, deterministic Light ATS using pure Python logic.
    Implements synonym mapping, normalization, and base-skill matching.
    """
    
    # 1. Advanced Synonym Map (Base Skill -> List of variations)
    # Long strings don't necessarily need exact \b boundaries, but short ones do.
    SYNONYM_MAP = {
        "python": ["python"],
        "java": ["java"],
        "javascript": ["javascript", "js"],
        "typescript": ["typescript", "ts"],
        "sql": ["sql", "mysql", "postgresql", "postgres", "no-sql", "nosql"],
        "aws": ["aws", "amazon web services"],
        "docker": ["docker"],
        "kubernetes": ["kubernetes", "k8s"],
        "machine learning": ["machine learning", "ml"],
        "deep learning": ["deep learning", "dl"],
        "tensorflow": ["tensorflow", "tf"],
        "pandas": ["pandas"],
        "numpy": ["numpy"],
        "excel": ["excel"],
        "power bi": ["power bi", "powerbi"],
        "tableau": ["tableau"],
        "django": ["django"],
        "flask": ["flask"],
        "react": ["react", "react.js", "reactjs"],
        "node.js": ["node.js", "nodejs", "node"],
        "vue": ["vue", "vue.js", "vuejs"],
        "git": ["git", "github", "gitlab"],
        "c++": ["c++", "cpp"],
        "c#": ["c#", "c sharp"],
        "go": ["go", "golang"],
        "ruby": ["ruby", "ruby on rails"],
        "spring": ["spring", "spring boot"],
        "azure": ["azure"],
        "gcp": ["gcp", "google cloud platform", "google cloud"],
        "ci/cd": ["ci/cd", "ci-cd", "continuous integration"],
        "data analysis": ["data analysis", "data analytics"],
        "agile": ["agile", "scrum"],
        "html": ["html", "html5"],
        "css": ["css", "css3"],
        "rest api": ["rest api", "rest", "restful"],
        "graphql": ["graphql"]
    }
    
    # Helper to find base skill for any given string
    def get_base_skill(raw_skill):
        raw_skill = str(raw_skill).lower().strip()
        for base, synonyms in SYNONYM_MAP.items():
            if raw_skill in synonyms:
                return base
        return raw_skill

    # 2. Extract Job Skills (lowercase normalization)
    job_desc = str(job.get("description", "")).lower()
    job_skills_set = set()
    
    for base_skill, synonyms in SYNONYM_MAP.items():
        for syn in synonyms:
            # For very short synonyms (<=3 chars or 'java'), enforce strict word boundary
            # to avoid matching 'java' in 'javascript' or 'go' in 'good'
            if len(syn) <= 3 or syn in ["java", "react", "node", "git"]:
                # Special handling for C++ / C# because \b fails on symbols
                if syn == "c++":
                    if "c++" in job_desc: job_skills_set.add(base_skill)
                elif syn == "c#":
                    if "c#" in job_desc: job_skills_set.add(base_skill)
                elif re.search(r'\b' + re.escape(syn) + r'\b', job_desc):
                    job_skills_set.add(base_skill)
            else:
                # Partial/Substring match allowed for longer distinctive skills
                if syn in job_desc:
                    job_skills_set.add(base_skill)

    # 3. Extract Resume Skills (normalization to Base Skills)
    resume_skills_raw = resume_data.get("skills", [])
    resume_skills_set = set()
    for s in resume_skills_raw:
        skill_name = str(s.get("name", s) if isinstance(s, dict) else s)
        base = get_base_skill(skill_name)
        resume_skills_set.add(base)
        
    # 4. Matching Logic (Set Operations)
    matched_skills = resume_skills_set.intersection(job_skills_set)
    missing_skills = job_skills_set.difference(resume_skills_set)
    
    # Calculate a quick match score for ranking
    match_score = 0
    if job_skills_set:
        match_score = int((len(matched_skills) / len(job_skills_set)) * 100)
    else:
        match_score = 50 
        
    # Formatting lists and prioritization (Top 5)
    req_list = list(job_skills_set)
    matched_list = list(matched_skills)
    missing_list = list(missing_skills)

    return {
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "match_score": match_score,
        "required_skills": [s.title() for s in req_list[:5]],
        "matched_skills": [s.title() for s in matched_list],
        "missing_skills": [s.title() for s in missing_list[:5]],
        "apply_link": job.get("apply_link", "")
    }

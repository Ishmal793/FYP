import hashlib
from django.db import transaction
from resumes.models import Resume
from fast_nlp_layer.nlp_utils import basic_nlp_parse
from vector_engine.embedding_service import generate_embedding, get_document_string
import json
import os

class WorkflowOrchestrator:
    """Central Controller for the AI Pipeline DAG ensuring reactive data freshness"""

    @classmethod
    def generate_hash(cls, parsed_data: dict) -> str:
        """Create a deterministic hash of the resume data to detect deep changes."""
        if not parsed_data:
            return "empty"
        # Serialize with sorted keys to avoid dictionary ordering causing false-changes
        serialized = json.dumps(parsed_data, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()

    @classmethod
    @transaction.atomic
    def process_resume_update(cls, resume_id: int):
        """
        Called whenever `parsed_data` is saved. Triggers downstream reset and Normalization if a hash mismatch triggers.
        """
        try:
            resume = Resume.objects.select_for_update().get(id=resume_id)
        except Resume.DoesNotExist:
            return False

        new_hash = cls.generate_hash(resume.parsed_data)

        # Reactive workflow trigger
        if resume.resume_hash == new_hash:
            # Data didn't genuinely change, no need to clear the DAG
            return True

        # State is dirty. Lock profile and trigger pipeline reset.
        resume.resume_hash = new_hash
        resume.pipeline_status = "RECOMPUTING"
        resume.save()

        # --- LAYER 1: Fast NLP Preprocessing (No LLM) ---
        print(f"[ORCHESTRATOR] Starting Fast NLP Layer for Resume {resume_id}")
        
        # Use the structured skills dictionary
        skills_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents_resume_parser', 'skills_dict.json')
        try:
            with open(skills_path, 'r') as f:
                skill_dict = json.load(f)
        except Exception as e:
            print(f"[ORCHESTRATOR] Error loading skills_dict: {e}")
            skill_dict = {}
        
        raw_text = resume.parsed_data.get('raw_text', '')
        if raw_text:
            fast_results = basic_nlp_parse(raw_text, skill_dict)
            print(f"[ORCHESTRATOR] Domain Detected: {fast_results.get('detected_domain')}")
            # Merge fast results into parsed_data
            resume.parsed_data.update(fast_results)
            resume.save(update_fields=['parsed_data'])

        # --- LAYER 1.5: Vector Generation & Indexing ---
        print(f"[ORCHESTRATOR] Starting Vector Layer for Resume {resume_id}")
        doc_string = get_document_string(resume.parsed_data)
        embedding = generate_embedding(doc_string)
        if embedding:
            resume.vector_embedding = embedding
            resume.save(update_fields=['vector_embedding'])
            
            # Note: Indexing into FAISS normally happens in batch or on-demand for HR search
            # to ensure the index stays in sync with the DB.

        resume.pipeline_status = "COMPLETED"
        resume.save(update_fields=['pipeline_status'])
        
        return True

    @classmethod
    @transaction.atomic
    def process_profile_update(cls, user_id: int):
        """
        Triggered when a CareerProfile is updated. Syncs the vector embedding.
        """
        from accounts.models import CareerProfile
        try:
            profile = CareerProfile.objects.select_for_update().get(user_id=user_id)
        except CareerProfile.DoesNotExist:
            return False

        # Compile profile text for embedding
        profile_text = f"""
        Target Role: {profile.target_job_role}
        Skills: {', '.join(profile.skills)}
        Experience: {profile.experience}
        Education: {profile.education_level}
        """
        
        embedding = generate_embedding(profile_text)
        if embedding:
            profile.vector_embedding = embedding
            profile.save(update_fields=['vector_embedding'])
            print(f"[ORCHESTRATOR] Updated Vector Layer for Profile of User {user_id}")
            
        return True

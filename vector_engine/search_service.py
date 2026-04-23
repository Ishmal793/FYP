import numpy as np
from resumes.models import Resume
from accounts.models import CareerProfile

class VectorSearchService:
    @staticmethod
    def find_top_candidates(query_embedding, target_domain, limit=20):
        """
        Hybrid Semantic Search: 
        1. Filters by Domain & Searchability in SQLite
        2. Computes Similarity using Optimized Numpy (FAISS-equivalent)
        """
        # Fetch only candidates with embeddings and correct domain
        profiles = CareerProfile.objects.filter(
            is_searchable=True
        ).exclude(vector_embedding__isnull=True)
        
        candidates = []
        for p in profiles:
            # Domain check (retrieved from latest resume)
            latest_resume = Resume.objects.filter(user=p.user).order_by('-created_at').first()
            if not latest_resume: continue
            
            candidate_domain = latest_resume.parsed_data.get("detected_domain", "Unclear")
            if target_domain != "Unclear" and candidate_domain != "Unclear" and target_domain != candidate_domain:
                continue
                
            # Cosine similarity
            sim = np.dot(query_embedding, p.vector_embedding)
            candidates.append((p, sim, latest_resume))
            
        # Sort and limit
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:limit]

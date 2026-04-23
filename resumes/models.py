from django.db import models
from accounts.models import CustomUser

class Resume(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="resumes")
    file = models.FileField(upload_to="resumes/", null=True, blank=True)
    parsed_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # State Management for Orchestrator DAG
    resume_hash = models.CharField(max_length=64, blank=True, null=True, help_text="SHA-256 hash of parsed_data to detect changes")
    pipeline_status = models.CharField(max_length=50, default="IDLE", choices=[
        ("IDLE", "Idle"),
        ("RECOMPUTING", "Recomputing Pipeline"),
        ("COMPLETED", "Completed Pipeline"),
        ("ERROR", "Pipeline Error")
    ])
    
    # Workflow Stage 5 Memory
    locked_target_role = models.CharField(max_length=255, blank=True, null=True)
    locked_jd = models.TextField(blank=True, null=True, help_text="The Auto-Generated Market Job Description")

    # ATS Module Tracking
    ats_completed = models.BooleanField(default=False)
    ats_score_overall = models.IntegerField(null=True, blank=True)
    skill_gap_data = models.JSONField(default=dict, blank=True)
    cv_variants = models.JSONField(default=dict, blank=True)
    
    # Vector Search Field
    vector_embedding = models.JSONField(null=True, blank=True, help_text="Sentence-BERT embedding for semantic search")

    def __str__(self):
        return f"Resume of {self.user.email}"

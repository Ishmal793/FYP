from django.db import models
from django.conf import settings
from resumes.models import Resume

class JobResult(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_jobs')
    resume = models.ForeignKey(Resume, on_delete=models.SET_NULL, null=True, blank=True, related_name='matched_jobs')
    job_title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    location = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField()
    job_url = models.URLField(max_length=500, null=True, blank=True)
    
    overall_score = models.IntegerField(default=0)
    score_breakdown = models.JSONField(default=dict, blank=True)
    details = models.JSONField(default=dict, blank=True)
    missing_keywords = models.JSONField(default=list, blank=True)
    searchability = models.JSONField(default=dict, blank=True)
    recruiter_tips = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.email} - {self.job_title} ({self.overall_score}/100)"

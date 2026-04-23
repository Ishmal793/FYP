from django.db import models
from accounts.models import CustomUser
from resumes.models import Resume

class JobResult(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="job_results")
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="job_results")
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    description = models.TextField()
    apply_link = models.URLField(max_length=500, unique=True)
    match_score = models.IntegerField(default=0)
    missing_skills = models.JSONField(default=list)
    required_skills = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'resume', '-match_score']),
        ]
        ordering = ['-match_score']

    def __str__(self):
        return f"{self.title} at {self.company} ({self.match_score}%)"

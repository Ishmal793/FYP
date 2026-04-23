from django.db import models
from django.conf import settings
from resumes.models import Resume
from jobs.models import JobResult

class SkillGapReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='skill_gaps')
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='skill_gaps')
    target_job = models.ForeignKey(JobResult, on_delete=models.SET_NULL, null=True, blank=True)
    target_role_title = models.CharField(max_length=255)
    missing_skills = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Gap Analysis for {self.user.email} - {self.target_role_title}"

class CourseRecommendation(models.Model):
    report = models.ForeignKey(SkillGapReport, on_delete=models.CASCADE, related_name='recommendations')
    skill = models.CharField(max_length=100)
    course_title = models.CharField(max_length=255)
    platform = models.CharField(max_length=100)
    duration_estimate = models.CharField(max_length=100)
    url = models.URLField(max_length=500, null=True, blank=True)
    
    def __str__(self):
        return f"{self.course_title} ({self.platform})"

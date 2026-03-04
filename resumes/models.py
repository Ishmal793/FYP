from django.db import models
from accounts.models import CustomUser

class Resume(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="resumes")
    file = models.FileField(upload_to="resumes/", null=True, blank=True)
    parsed_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Resume of {self.user.email}"

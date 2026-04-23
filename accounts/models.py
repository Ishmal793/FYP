from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'hr')
        
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('job_seeker', 'Job Seeker'),
        ('hr', 'HR / Recruiter'),
    )
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='job_seeker')
    
    # Shared Fields
    name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # Job Seeker Fields
    date_of_birth = models.DateField(null=True, blank=True)
    last_degree = models.CharField(max_length=255, blank=True, null=True)
    current_degree = models.CharField(max_length=255, blank=True, null=True)
    student_or_graduate = models.CharField(max_length=50, blank=True, null=True)
    field_of_study = models.CharField(max_length=255, blank=True, null=True)
    university = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    
    # HR Fields
    company_name = models.CharField(max_length=255, blank=True, null=True)
    company_address = models.TextField(blank=True, null=True)
    designation = models.CharField(max_length=255, blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    has_completed_onboarding = models.BooleanField(default=False)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    def __str__(self):
        return self.email

class CareerProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='career_profile')
    education_level = models.CharField(max_length=100, blank=True, null=True)
    graduation_year = models.CharField(max_length=20, blank=True, null=True)
    cgpa = models.CharField(max_length=50, blank=True, null=True)
    
    career_level = models.CharField(max_length=100, blank=True, null=True)
    experience = models.CharField(max_length=100, blank=True, null=True)
    target_job_role = models.CharField(max_length=255, blank=True, null=True)
    
    preferred_job_type = models.JSONField(default=list, blank=True)
    preferred_locations = models.JSONField(default=list, blank=True)
    interested_industries = models.JSONField(default=list, blank=True)
    
    linkedin_url = models.URLField(max_length=500, blank=True, null=True)
    portfolio_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Structured Data for Career Profile Memory
    skills = models.JSONField(default=list, blank=True)
    experience_list = models.JSONField(default=list, blank=True)
    projects = models.JSONField(default=list, blank=True)
    education_list = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    
    # Search & Privacy Controls
    is_searchable = models.BooleanField(default=True, help_text="Allow HR/Recruiters to find this profile")
    vector_embedding = models.JSONField(null=True, blank=True, help_text="Semantic vector for quick matching")
    
    def __str__(self):
        return f"{self.user.email} - Profile"

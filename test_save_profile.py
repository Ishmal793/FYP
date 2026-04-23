import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'career_platform.settings')
django.setup()

from accounts.models import CustomUser
from accounts.serializers import CareerProfileSerializer
import traceback

try:
    user = CustomUser.objects.last()
    
    # Simulate JS payload
    data = {"education_level": "Bachelor's Degree", "graduation_year": "2024", "cgpa": "3.5",
            "career_level": "Fresher / Entry Level", "experience": "0 years", "target_job_role": "Software Engineer",
            "preferred_job_type": ["Full-time"], "preferred_locations": ["Remote"],
            "interested_industries": ["IT / Software"]}
            
    print(f"Testing posting profile for user: {user.email}")
    
    if hasattr(user, 'career_profile'):
        print("Profile exists, applying partial update...")
        serializer = CareerProfileSerializer(user.career_profile, data=data, partial=True)
    else:
        print("Profile does NOT exist, creating new...")
        serializer = CareerProfileSerializer(data=data)
        
    print(f"Is valid? {serializer.is_valid()}")
    if not serializer.is_valid():
        print("Errors:", serializer.errors)
    else:
        print("Attempting to save...")
        obj = serializer.save(user=user)
        print(f"Successfully saved profile ID: {obj.id}")
except Exception as e:
    print("Crash Output:")
    traceback.print_exc()

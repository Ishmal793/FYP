import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'career_platform.settings')
django.setup()

from accounts.models import CustomUser
from accounts.serializers import UserSerializer
import traceback

try:
    user = CustomUser.objects.last()
    if user:
        print(f"Testing serialization for user: {user.email}")
        serializer = UserSerializer(user)
        print("Data:")
        print(serializer.data)
    else:
        print("No users found.")
except Exception as e:
    print("Serialization Failed!")
    traceback.print_exc()

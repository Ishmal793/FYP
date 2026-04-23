from django.urls import path
from .views import CareerCoachChatView

urlpatterns = [
    path('chat/', CareerCoachChatView.as_view(), name='career_coach_chat'),
]

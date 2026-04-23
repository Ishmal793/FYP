from django.urls import path
from .views import CalculateLockedATSView, OptimizeCVView, SkillGapAdvisorView

urlpatterns = [
    path('match/', CalculateLockedATSView.as_view(), name='match-ats'),
    path('optimize/', OptimizeCVView.as_view(), name='optimize-cv'),
    path('advise-courses/', SkillGapAdvisorView.as_view(), name='advise-courses'),
]

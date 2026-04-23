from django.urls import path
from .views import AdvancedJobMatchAnalysisView, RecruiterMatchView

urlpatterns = [
    path('score/', AdvancedJobMatchAnalysisView.as_view(), name='advanced_job_match'),
    path('hr/rank/', RecruiterMatchView.as_view(), name='hr_rank_candidates'),
]

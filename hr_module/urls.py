from django.urls import path
from .views import HRDashboardStatsView, HRJobMatchView, HRCandidateDetailView

urlpatterns = [
    path('dashboard/', HRDashboardStatsView.as_view(), name='hr_dashboard_stats'),
    path('job-match/', HRJobMatchView.as_view(), name='hr_job_match'),
    path('candidate/<int:user_id>/', HRCandidateDetailView.as_view(), name='hr_candidate_detail'),
]

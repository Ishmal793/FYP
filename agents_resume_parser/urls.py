from django.urls import path
from .views import ParseResumeView, UpdateParsedResumeView, CompletedResumesListView, MarkAtsCompletedView

urlpatterns = [
    path('parse/', ParseResumeView.as_view(), name='parse_resume'),
    path('update-parsed/<int:resume_id>/', UpdateParsedResumeView.as_view(), name='update_parsed_resume'),
    path('completed/', CompletedResumesListView.as_view(), name='completed_resumes_list'),
    path('mark-completed/', MarkAtsCompletedView.as_view(), name='mark_ats_completed'),
]

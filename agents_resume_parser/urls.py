from django.urls import path
from .views import ParseResumeView

urlpatterns = [
    path('parse/', ParseResumeView.as_view(), name='parse_resume'),
]

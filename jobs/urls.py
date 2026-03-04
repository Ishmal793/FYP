from django.urls import path
from .views import JobHistoryAPIView

urlpatterns = [
    path('history/', JobHistoryAPIView.as_view(), name='job-history'),
]

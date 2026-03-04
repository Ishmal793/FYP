from django.urls import path
from .views import ReadinessScoreView

urlpatterns = [
    path('score/', ReadinessScoreView.as_view(), name='score-readiness'),
]

from django.urls import path
from .views import JobPredictionView

urlpatterns = [
    path('predict/', JobPredictionView.as_view(), name='predict-jobs'),
]

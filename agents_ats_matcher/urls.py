from django.urls import path
from .views import ATSMatcherBatchView

urlpatterns = [
    path('match/', ATSMatcherBatchView.as_view(), name='match-ats'),
]

from django.urls import path
from .views import FieldClassificationView, CareerAnalysisView

urlpatterns = [
    path('classify/', FieldClassificationView.as_view(), name='classify-field'),
    path('analyze/', CareerAnalysisView.as_view(), name='analyze-career'),
]

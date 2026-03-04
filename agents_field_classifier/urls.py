from django.urls import path
from .views import FieldClassificationView

urlpatterns = [
    path('classify/', FieldClassificationView.as_view(), name='classify-field'),
]

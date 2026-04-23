from django.urls import path
from .views import OptimizeCVView, ProfileMergeView

urlpatterns = [
    path('variants/', OptimizeCVView.as_view(), name='optimize_cv_variants'),
    path('profile/merge/', ProfileMergeView.as_view(), name='profile_merge_cv'),
]

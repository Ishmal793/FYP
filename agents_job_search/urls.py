from django.urls import path
from .views import JobSearchView, ToggleSaveJobView

urlpatterns = [
    path('search/', JobSearchView.as_view(), name='search-jobs'),
    path('save-job/', ToggleSaveJobView.as_view(), name='save-job'),
]

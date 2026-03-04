from django.urls import path
from .views import JobSearchView

urlpatterns = [
    path('search/', JobSearchView.as_view(), name='search-jobs'),
]

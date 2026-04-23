from django.urls import path
from . import views

urlpatterns = [
    path('trajectory/', views.generate_trajectory, name='generate_trajectory'),
]

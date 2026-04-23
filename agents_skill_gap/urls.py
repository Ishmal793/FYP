from django.urls import path
from . import views

urlpatterns = [
    path('roadmap/', views.generate_roadmap, name='generate_roadmap'),
]

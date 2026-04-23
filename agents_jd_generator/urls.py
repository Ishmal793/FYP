from django.urls import path
from .views import GenerateJDView, LockJDView

urlpatterns = [
    path('generate/', GenerateJDView.as_view(), name='generate_jd'),
    path('lock/<int:resume_id>/', LockJDView.as_view(), name='lock_jd'),
]

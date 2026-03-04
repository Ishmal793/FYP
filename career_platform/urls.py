"""
URL configuration for career_platform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/resume/", include("agents_resume_parser.urls")),
    path("api/readiness/", include("agents_readiness.urls")),
    path("api/jobs/", include("agents_job_predictor.urls")),
    path("api/search/", include("agents_job_search.urls")),
    path("api/ats/", include("agents_ats_matcher.urls")),
    path("api/profile/jobs/", include("jobs.urls")),
    path("", RedirectView.as_view(url='/login/')),
    path("login/", TemplateView.as_view(template_name="login.html"), name="login"),
    path("signup/", TemplateView.as_view(template_name="signup.html"), name="signup"),
    path("dashboard/", TemplateView.as_view(template_name="dashboard.html"), name="dashboard"),
    path("profile/", TemplateView.as_view(template_name="profile.html"), name="profile"),
    path("api/fields/", include("agents_field_classifier.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

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
    path('api/matcher/', include('agents_job_matcher.urls')),
    path("api/profile/jobs/", include("jobs.urls")),
    path("", TemplateView.as_view(template_name="landing.html"), name="landing"),
    path("home/", TemplateView.as_view(template_name="home.html"), name="home"),
    path("join/", TemplateView.as_view(template_name="role_selection.html"), name="join"),
    path("login/", TemplateView.as_view(template_name="login.html"), name="login"),
    path("signup/", TemplateView.as_view(template_name="signup.html"), name="signup"),
    path("questionnaire/", TemplateView.as_view(template_name="questionnaire.html"), name="questionnaire"),
    path("dashboard/", TemplateView.as_view(template_name="dashboard.html"), name="dashboard"),
    path("dashboard/ats/", TemplateView.as_view(template_name="ats_dashboard.html"), name="ats_dashboard"),
    path("dashboard/jobs/", TemplateView.as_view(template_name="job_search_dashboard.html"), name="job_search_dashboard"),
    path("dashboard/hr/", TemplateView.as_view(template_name="hr_dashboard.html"), name="hr_dashboard"),
    path("profile/", TemplateView.as_view(template_name="profile.html"), name="profile"),
    path("api/fields/", include("agents_field_classifier.urls")),
    path("api/jd/", include("agents_jd_generator.urls")),
    path("api/gap/", include("agents_skill_gap.urls")),
    path("api/career/", include("agents_career_path.urls")),
    path("api/optimizer/", include("agents_cv_optimizer.urls")),
    path("api/coach/", include("agents_career_coach.urls")),
    path("api/hr-module/", include("hr_module.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

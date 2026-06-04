"""
URL configuration for habit_coach_ai project.

See https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),  # /accounts/login/, /accounts/logout/, /accounts/password_*/
    path("", include("accounts.urls")),  # /register/, /
]

from django.contrib import admin
from django.urls import include, path
from django.contrib.auth.views import LoginView, LogoutView

urlpatterns = [path("admin/", admin.site.urls), path("accounts/login/", LoginView.as_view(template_name="registration/login.html"), name="login"),
               path("accounts/logout/", LogoutView.as_view(), name="logout"), path("api/", include("datapilot.urls"))]

from django.urls import path, include
from django.shortcuts import render
from django.contrib.auth import views as auth_views

# Početna stranica koja će prikazivati Dashboard
def home(request):
    return render(request, "core/home.html")

urlpatterns = [
    path("", home, name="home"),  # ✅ Početna stranica
    path("nurse/", include("nurse.urls")),  # ✅ Dodan nurse.urls
    path("login/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
]

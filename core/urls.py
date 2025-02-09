from django.urls import path, include
from django.shortcuts import render

# Početna stranica koja će prikazivati Dashboard
def home(request):
    return render(request, "core/home.html")

urlpatterns = [
    path("", home, name="home"),  # ✅ Početna stranica
    path("nurse/", include("nurse.urls")),  # ✅ Dodan nurse.urls
]

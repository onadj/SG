from django.urls import path
from .views import nurse_schedule # Uvezi funkciju koja generira raspored

urlpatterns = [
    path('schedule/', nurse_schedule, name='nurse_schedule'),  # ✅ Ispravno
]


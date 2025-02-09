from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import Shift

@login_required
def nurse_schedule(request):
    shifts = Shift.objects.all().order_by("date", "start_time")
    
    # Generiranje URL-ova za admin edit ako nema zaposlenika
    for shift in shifts:
        if shift.employee is None:
            shift.admin_edit_url = reverse('admin:nurse_shift_change', args=[shift.id])

    return render(request, "nurse/schedule.html", {"shifts": shifts})

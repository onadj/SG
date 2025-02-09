import pandas as pd
import csv
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Shift
from .utils import generate_nurse_schedule
from datetime import date, timedelta
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Shift, Employee
import json
from django.contrib.auth.decorators import login_required

@login_required
def nurse_schedule(request):
    shifts = Shift.objects.all().order_by("date", "start_time")
    employees = Employee.objects.all()
    
    return render(request, "nurse/schedule.html", {"shifts": shifts, "employees": employees})


@login_required
def generate_schedule(request):
    start_date = date(2025, 2, 10)
    end_date = date(2025, 2, 16)

    for single_date in (start_date + timedelta(n) for n in range((end_date - start_date).days + 1)):
        generate_nurse_schedule(single_date)

    return JsonResponse({"status": "success", "message": "Schedule generated successfully!"})

@login_required
def export_schedule_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="nurse_schedule.csv"'

    writer = csv.writer(response)
    writer.writerow(["Employee", "Department", "Role", "Date", "Start Time", "End Time", "Total Hours"])

    for shift in Shift.objects.all():
        writer.writerow([
            f"{shift.employee.first_name} {shift.employee.last_name}" if shift.employee else "⚠️ Worker Missing",
            shift.department.name if shift.department else "N/A",
            shift.role.name if shift.role else "⚠️ Role Missing",
            shift.date,
            shift.start_time,
            shift.end_time,
            shift.calculate_total_hours()
        ])

    return response

@login_required
def export_schedule_excel(request):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="nurse_schedule.xlsx"'

    df = pd.DataFrame([
        [
            f"{shift.employee.first_name} {shift.employee.last_name}" if shift.employee else "⚠️ Worker Missing",
            shift.department.name if shift.department else "N/A",
            shift.role.name if shift.role else "⚠️ Role Missing",
            shift.date,
            shift.start_time,
            shift.end_time,
            shift.calculate_total_hours()
        ]
        for shift in Shift.objects.all()
    ], columns=["Employee", "Department", "Role", "Date", "Start Time", "End Time", "Total Hours"])

    df.to_excel(response, index=False)
    return response

@csrf_exempt  # Omogućava brisanje bez problema s CSRF tokenom
@login_required
def delete_shift(request, shift_id):
    if request.method == "POST":
        shift = get_object_or_404(Shift, id=shift_id)
        shift.delete()
        return JsonResponse({"status": "success", "message": "Shift deleted successfully!"})
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


@csrf_exempt
@login_required
def delete_shift(request, shift_id):
    if request.method == "POST":
        shift = get_object_or_404(Shift, id=shift_id)
        shift.delete()
        return JsonResponse({"status": "success", "message": "Shift deleted successfully!"})
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)

@csrf_exempt
@login_required
def edit_shift(request, shift_id):
    if request.method == "POST":
        shift = get_object_or_404(Shift, id=shift_id)
        data = json.loads(request.body)

        try:
            shift.employee = Employee.objects.get(id=data["employee"]) if data["employee"] else None
            shift.date = data["date"]
            shift.start_time = data["start_time"]
            shift.end_time = data["end_time"]
            shift.save()

            return JsonResponse({"status": "success", "message": "Shift updated successfully!"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)
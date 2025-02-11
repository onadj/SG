import pandas as pd
import csv
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Shift, Employee, ShiftRequirement
from .utils import generate_nurse_schedule
from datetime import date, timedelta
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import json

@login_required
def nurse_schedule(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    shifts = Shift.objects.all().order_by("date", "start_time")
    shift_requirements = ShiftRequirement.objects.all()

    if start_date and end_date:
        shifts = shifts.filter(date__range=[start_date, end_date])
        shift_requirements = shift_requirements.filter(date__range=[start_date, end_date])

    employees = Employee.objects.all()

    # 📌 Ispravan izračun ukupnih dodijeljenih sati
    total_assigned_hours = 0
    employee_hours = {}

    for shift in shifts:
        if shift.employee:
            # ✅ Ispravi grešku kod smjena koje prelaze ponoć
            start_time = shift.start_time
            end_time = shift.end_time

            if end_time <= start_time:  # Ako prelazi preko ponoći
                shift_hours = (24 - start_time.hour) + end_time.hour
            else:
                shift_hours = end_time.hour - start_time.hour
            
            total_assigned_hours += shift_hours

            full_name = f"{shift.employee.first_name} {shift.employee.last_name}"
            employee_hours[full_name] = employee_hours.get(full_name, 0) + shift_hours

    # 📌 Izračun potrebnih sati iz ShiftRequirement
    total_required_hours = sum(req.required_hours for req in shift_requirements)

    # 📌 Postotak popunjenosti smjena
    percent_filled = (total_assigned_hours / total_required_hours) * 100 if total_required_hours else 0

    context = {
        "shifts": shifts,
        "employees": employees,
        "total_assigned_hours": total_assigned_hours,
        "total_required_hours": total_required_hours,
        "percent_filled": percent_filled,
        "employee_hours": employee_hours,
        "start_date": start_date,
        "end_date": end_date,
    }
    
    return render(request, "nurse/schedule.html", context)



@login_required
def generate_schedule(request):
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    if start_date_str and end_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            return JsonResponse({"status": "error", "message": "Invalid date format!"}, status=400)
    else:
        start_date = date.today()
        end_date = start_date + timedelta(days=6)  # Ako nema unosa, generira se za sljedeću sedmicu

    for single_date in (start_date + timedelta(n) for n in range((end_date - start_date).days + 1)):
        generate_nurse_schedule(single_date)

    return JsonResponse({"status": "success", "message": f"Schedule generated from {start_date} to {end_date}!"})

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

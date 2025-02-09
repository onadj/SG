from datetime import datetime, timedelta
from django.utils.timezone import now
from django.apps import apps
import random
from collections import defaultdict

def generate_nurse_schedule(custom_date):
    ShiftRequirement = apps.get_model('nurse', 'ShiftRequirement')
    Shift = apps.get_model('nurse', 'Shift')
    Employee = apps.get_model('nurse', 'Employee')
    ShiftType = apps.get_model('nurse', 'ShiftType')

    deleted_count, _ = Shift.objects.filter(date=custom_date).delete()
    print(f"\n🗑️ Obrišeno {deleted_count} smjena za {custom_date}, generiram novi raspored...\n")

    shifts = []
    employee_hours = defaultdict(int)
    assigned_employees = set()

    shift_requirements = ShiftRequirement.objects.filter(date=custom_date)
    if not shift_requirements.exists():
        print("⚠️ Nema ShiftRequirement unosa za ovaj dan!")
        return shifts

    for requirement in shift_requirements:
        total_hours_needed = requirement.required_hours
        assigned_hours = 0

        print(f"\n📌 Obrada {requirement.department.name} za {requirement.date.strftime('%A')} ({requirement.date})")
        print(f"📊 Potrebno sati: {total_hours_needed}h")

        available_employees = list(Employee.objects.filter(
            departments=requirement.department,
            available_days__name=requirement.date.strftime('%A'),
            roles__in=requirement.required_roles.all()
        ).distinct())
        random.shuffle(available_employees)

        if not available_employees:
            print("⚠️ NEMA DOSTUPNIH RADNIKA! Ostavlja se oznaka nedostajućeg radnika u shifts tabeli.")
            create_missing_shift(requirement)
            continue

        if total_hours_needed == 24:
            shift_structure = random.choice([
                ["08-20", "08-20"],
                ["08-20", "08-14", "14-20"],
                ["08-14", "08-14", "14-20", "14-20"]
            ])
        else:
            shift_structure = ["20-08"]

        for shift_name in shift_structure:
            try:
                shift_type = ShiftType.objects.get(name=shift_name)
            except ShiftType.DoesNotExist:
                print(f"⚠️ Smjena '{shift_name}' ne postoji u bazi!")
                continue

            employees_for_shift = find_available_employees(available_employees, employee_hours, shift_type, assigned_employees, shifts)
            if not employees_for_shift:
                continue

            for employee in employees_for_shift[:1]:  # Svaka smjena dobiva jednog radnika
                create_shift(employee, requirement, shift_type, shifts, employee_hours, assigned_employees)
                assigned_hours += shift_type.duration_hours

        print(f"\n👥 Radnici dodijeljeni za {requirement.date} ({requirement.department.name}): {', '.join([f'{e.first_name} {e.last_name}' for e in assigned_employees])}")
        print(f"📊 Ukupno sati pokriveno: {assigned_hours}/{total_hours_needed}")

    print("\n✅✅ **Raspored generiran uspješno!** ✅✅")
    return shifts

def find_available_employees(available_employees, employee_hours, shift_type, assigned_employees, shifts):
    selected_employees = []
    random.shuffle(available_employees)
    
    for employee in available_employees:
        total_assigned_hours = employee_hours[employee]
        
        if total_assigned_hours >= employee.max_weekly_hours:
            continue

        if any(shift.employee == employee and shift.start_time == shift_type.start_time and shift.end_time == shift_type.end_time for shift in shifts):
            continue

        if total_assigned_hours + shift_type.duration_hours <= employee.max_weekly_hours and employee not in assigned_employees:
            if not check_shift_overlap(employee, shift_type, shifts):
                selected_employees.append(employee)
    return selected_employees[:1]

def check_shift_overlap(employee, shift_type, shifts):
    for shift in shifts:
        if shift.employee == employee:
            if not (shift.end_time <= shift_type.start_time or shift.start_time >= shift_type.end_time):
                return True
    return False

def create_shift(employee, requirement, shift_type, shifts, employee_hours, assigned_employees):
    Shift = apps.get_model('nurse', 'Shift')

    shift = Shift(
        employee=employee,
        department=requirement.department,
        role=employee.roles.first(),
        date=requirement.date,
        start_time=shift_type.start_time,
        end_time=shift_type.end_time
    )
    shift.save()
    shifts.append(shift)
    employee_hours[employee] += shift_type.duration_hours
    assigned_employees.add(employee)

def create_missing_shift(requirement):
    Shift = apps.get_model('nurse', 'Shift')
    missing_shift = Shift(
        employee=None,
        department=requirement.department,
        role=None,
        date=requirement.date,
        start_time=None,
        end_time=None
    )
    missing_shift.save()

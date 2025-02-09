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
    employee_hours = {emp: sum(shift.calculate_total_hours() for shift in Shift.objects.filter(employee=emp)) for emp in Employee.objects.all()}
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

        available_employees.sort(key=lambda e: employee_hours.get(e, 0))  # Prioritet radnicima s najmanje sati

        shift_structure = determine_shift_structure(total_hours_needed)

        for shift_name in shift_structure:
            try:
                shift_type = ShiftType.objects.get(name=shift_name)
            except ShiftType.DoesNotExist:
                print(f"⚠️ Smjena '{shift_name}' ne postoji u bazi!")
                continue

            employees_for_shift = find_available_employees(available_employees, employee_hours, shift_type, assigned_employees, shifts)
            if not employees_for_shift:
                print(f"⚠️ Nema radnika za smjenu {shift_name}. Ostavlja se nepopunjeno!")
                create_missing_shift(requirement, shift_type)
                continue

            for employee in employees_for_shift[:1]:  # Svaka smjena dobiva jednog radnika
                create_shift(employee, requirement, shift_type, shifts, employee_hours, assigned_employees)
                assigned_hours += shift_type.duration_hours

        print(f"\n👥 Radnici dodijeljeni za {requirement.date} ({requirement.department.name}): {', '.join([f'{e.first_name} {e.last_name}' for e in assigned_employees])}")
        print(f"📊 Ukupno sati pokriveno: {assigned_hours}/{total_hours_needed}")

    check_exceeded_hours(employee_hours)
    print("\n✅✅ **Raspored generiran uspješno!** ✅✅")
    return shifts

def determine_shift_structure(total_hours_needed):
    if total_hours_needed == 24:
        return random.choice([
            ["08-20", "08-20"],
            ["08-20", "08-14", "14-20"],
            ["08-14", "08-14", "14-20", "14-20"]
        ])
    return ["20-08"]

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

def create_missing_shift(requirement, shift_type=None):
    Shift = apps.get_model('nurse', 'Shift')
    missing_shift = Shift(
        employee=None,
        department=requirement.department,
        role=None,
        date=requirement.date,
        start_time=shift_type.start_time if shift_type else None,
        end_time=shift_type.end_time if shift_type else None
    )
    missing_shift.save()

def check_exceeded_hours(employee_hours):
    exceeded = [emp for emp, hours in employee_hours.items() if hours > emp.max_weekly_hours]
    if exceeded:
        print("⚠️ SLJEDEĆI RADNICI IMAJU VIŠE SATI NEGO ŠTO SMIJU RADITI:")
        for emp in exceeded:
            print(f"⚠️ {emp.first_name} {emp.last_name} - Dodijeljeno: {employee_hours[emp]}h, Max: {emp.max_weekly_hours}h")

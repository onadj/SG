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

        shift_distribution = defaultdict(int, {shift.name: 0 for shift in ShiftType.objects.all()})

        print(f"\n📌 Obrada {requirement.department.name} za {requirement.date.strftime('%A')} ({requirement.date})")
        print(f"📊 Potrebno sati: {total_hours_needed}h")

        allowed_shifts = sorted(requirement.shift_types.all(), key=lambda x: x.start_time)
        available_employees = list(Employee.objects.filter(
            departments=requirement.department,
            available_days__name=requirement.date.strftime('%A'),
            roles__in=requirement.required_roles.all()
        ).distinct())
        random.shuffle(available_employees)

        if not available_employees:
            print("⚠️ NEMA DOSTUPNIH RADNIKA!")
            continue

        shift_combinations = [
            ["08-20", "08-20"],
            ["08-14", "14-20", "08-20"],
            ["08-14", "08-14", "14-20", "14-20"]
        ]
        shift_combinations_night = [
            ["20-08"]
        ]

        for combo in shift_combinations:
            for shift_name in combo:
                try:
                    shift_type = ShiftType.objects.get(name=shift_name)
                except ShiftType.DoesNotExist:
                    print(f"⚠️ Smjena '{shift_name}' ne postoji u bazi!")
                    continue

                shift_start, shift_end = shift_type.start_time, shift_type.end_time
                shift_duration = shift_type.duration_hours

                if assigned_hours >= total_hours_needed:
                    break

                employees_for_shift = find_available_employees(available_employees, employee_hours, shift_type, assigned_employees, shifts)
                if not employees_for_shift:
                    continue

                max_employees_needed = max(1, (total_hours_needed - assigned_hours) // shift_duration)
                employees_for_shift = employees_for_shift[:max_employees_needed]

                for employee in employees_for_shift:
                    if assigned_hours + shift_duration > total_hours_needed:
                        break

                    create_shift(employee, requirement, shift_start, shift_end, shift_duration, shifts, employee_hours, assigned_employees)
                    shift_distribution[shift_name] += 1
                    assigned_hours += shift_duration
                
                if assigned_hours >= total_hours_needed:
                    break
            
            if assigned_hours >= total_hours_needed:
                break

        for combo in shift_combinations_night:
            for shift_name in combo:
                try:
                    shift_type = ShiftType.objects.get(name=shift_name)
                except ShiftType.DoesNotExist:
                    print(f"⚠️ Smjena '{shift_name}' ne postoji u bazi!")
                    continue

                shift_start, shift_end = shift_type.start_time, shift_type.end_time
                shift_duration = shift_type.duration_hours

                if shift_end < shift_start:  # Noćna smjena prelazi u idući dan
                    shift_duration = (24 - shift_start.hour) + shift_end.hour

                employees_for_shift = find_available_employees(available_employees, employee_hours, shift_type, assigned_employees, shifts)
                if not employees_for_shift:
                    continue

                for employee in employees_for_shift[:1]:  # Noćna smjena uvijek samo 1 radnik
                    create_shift(employee, requirement, shift_start, shift_end, shift_duration, shifts, employee_hours, assigned_employees)
                    shift_distribution[shift_name] += 1

        print(f"\n👥 Radnici dodijeljeni za {requirement.date} ({requirement.department.name}): {', '.join([f'{e.first_name} {e.last_name}' for e in assigned_employees])}")
        print(f"📊 Ukupno sati pokriveno: {total_hours_needed}/{total_hours_needed}")

    print("\n✅✅ **Raspored generiran uspješno!** ✅✅")
    return shifts

# === FUNKCIJE ZA DODJELU SMJENA ===

def find_available_employees(available_employees, employee_hours, shift_type, assigned_employees, shifts):
    shift_duration = shift_type.duration_hours
    selected_employees = []
    random.shuffle(available_employees)
    
    for employee in available_employees:
        total_assigned_hours = employee_hours[employee]

        if total_assigned_hours >= employee.max_weekly_hours:
            continue

        if any(shift.employee == employee and shift.start_time == shift_type.start_time and shift.end_time == shift_type.end_time for shift in shifts):
            continue
        
        if total_assigned_hours + shift_duration <= employee.max_weekly_hours and employee not in assigned_employees:
            if not check_shift_overlap(employee, shift_type, shifts):
                selected_employees.append(employee)
        
        if len(selected_employees) >= 2:
            break
    return selected_employees

def check_shift_overlap(employee, shift_type, shifts):
    for shift in shifts:
        if shift.employee == employee:
            if not (shift.end_time <= shift_type.start_time or shift.start_time >= shift_type.end_time):
                return True
    return False

def create_shift(employee, requirement, shift_start, shift_end, shift_duration, shifts, employee_hours, assigned_employees):
    Shift = apps.get_model('nurse', 'Shift')

    existing_shift = Shift.objects.filter(
        employee=employee,
        department=requirement.department,
        date=requirement.date,
        start_time=shift_start,
        end_time=shift_end
    ).exists()

    if existing_shift:
        return

    shift = Shift(
        employee=employee,
        department=requirement.department,
        role=employee.roles.first(),
        date=requirement.date,
        start_time=shift_start,
        end_time=shift_end
    )
    shift.save()
    shifts.append(shift)

    employee_hours[employee] += shift_duration
    assigned_employees.add(employee)

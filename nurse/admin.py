from django.contrib import admin
from django.http import HttpResponse
import csv
import pandas as pd
from django.apps import apps
from .models import Department, Role, ShiftType, Employee, ShiftRequirement, Shift, TimeOff, Day
from nurse.utils import generate_nurse_schedule  # Uvoz skripte za generiranje rasporeda
from django.utils.timezone import now
from datetime import timedelta


# === 📌 DEPARTMENT ADMIN ===
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# === 📌 ROLE ADMIN ===
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'department')
    search_fields = ('name', 'department__name')
    list_filter = ('department',)

# === 📌 SHIFT TYPE ADMIN ===
@admin.register(ShiftType)
class ShiftTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_time', 'end_time', 'duration_hours')
    search_fields = ('name',)

# === 📌 EMPLOYEE ADMIN ===
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'get_departments', 'get_roles', 'max_weekly_hours', 'max_daily_hours', 'priority', 'get_total_hours_last_week')
    search_fields = ('first_name', 'last_name', 'departments__name', 'roles__name')
    list_filter = ('departments', 'roles', 'available_days', 'can_work_shifts')
    filter_horizontal = ('departments', 'roles', 'available_days', 'can_work_shifts')
    ordering = ('priority', '-max_weekly_hours')

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    get_full_name.short_description = "Full Name"

    def get_departments(self, obj):
        return ", ".join([d.name for d in obj.departments.all()])
    get_departments.short_description = "Departments"

    def get_roles(self, obj):
        return ", ".join([r.name for r in obj.roles.all()])
    get_roles.short_description = "Roles"

    def get_total_hours_last_week(self, obj):
        Shift = apps.get_model('nurse', 'Shift')
        last_week_shifts = Shift.objects.filter(employee=obj, date__gte=now().date() - timedelta(days=7))
        return sum(shift.calculate_total_hours() for shift in last_week_shifts)
    get_total_hours_last_week.short_description = "Total Hours Last 7 Days"

# === 📌 SHIFT ADMIN ===
@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('get_employee_full_name', 'department', 'get_role_name', 'date', 'start_time', 'end_time', 'corrected_total_hours', 'get_shift_configuration', 'missing_worker')
    search_fields = ('employee__first_name', 'employee__last_name', 'department__name', 'role__name', 'date')
    list_filter = ('department', 'role', 'date', 'start_time', 'end_time')
    ordering = ('date', 'start_time')
    actions = ['export_schedule_to_csv', 'export_schedule_to_excel', 'export_schedule_to_pdf', 'delete_all_shifts']

    def get_employee_full_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}" if obj.employee else "⚠️ Worker Missing"
    get_employee_full_name.short_description = "Employee"

    def get_role_name(self, obj):
        return obj.role.name if obj.role else "⚠️ Role Missing"
    get_role_name.short_description = "Role"

    def corrected_total_hours(self, obj):
        if obj.start_time > obj.end_time:  # Noćna smjena prelazi preko ponoći
            total_seconds = ((24 - obj.start_time.hour) + obj.end_time.hour) * 3600 + (obj.end_time.minute - obj.start_time.minute) * 60
        else:
            total_seconds = (obj.end_time.hour * 3600 + obj.end_time.minute * 60) - (obj.start_time.hour * 3600 + obj.start_time.minute * 60)
        return round(total_seconds / 3600, 2)
    corrected_total_hours.short_description = "Total Hours"

    def get_shift_configuration(self, obj):
        Shift = apps.get_model('nurse', 'Shift')
        ShiftType = apps.get_model('nurse', 'ShiftType')

        # Pravilno inicijaliziramo shift konfiguraciju
        shift_counts = {f"{shift.start_time.strftime('%H:%M')}-{shift.end_time.strftime('%H:%M')}": 0 for shift in ShiftType.objects.all()}

        # Dohvaćamo sve smjene za taj dan
        shifts_for_day = Shift.objects.filter(date=obj.date)

        for shift in shifts_for_day:
            shift_key = f"{shift.start_time.strftime('%H:%M')}-{shift.end_time.strftime('%H:%M')}"
            if shift_key in shift_counts:
                shift_counts[shift_key] += 1
            else:
                shift_counts[shift_key] = 1  # Inicijalizacija ako ne postoji
        
        return ", ".join([f"{key}: {value}" for key, value in shift_counts.items()])
    
    get_shift_configuration.short_description = "Daily Shift Configuration"

    def missing_worker(self, obj):
        return "⚠️ Worker Needed" if obj.employee is None else "✅ Filled"
    missing_worker.short_description = "Shift Status"

# === 📌 SHIFT REQUIREMENT ADMIN ===
@admin.register(ShiftRequirement)
class ShiftRequirementAdmin(admin.ModelAdmin):
    list_display = ('department', 'date', 'required_hours', 'get_shift_types', 'get_roles')
    search_fields = ('department__name', 'date', 'required_roles__name')
    list_filter = ('department', 'date')
    ordering = ('date', 'department')
    filter_horizontal = ('shift_types', 'required_roles')
    actions = ['generate_schedule']

    def get_shift_types(self, obj):
        return ", ".join([s.name for s in obj.shift_types.all()])
    get_shift_types.short_description = "Shift Types"

    def get_roles(self, obj):
        return ", ".join([r.name for r in obj.required_roles.all()])
    get_roles.short_description = "Required Roles"

    @admin.action(description="✅ Generate schedule for selected shifts")
    def generate_schedule(self, request, queryset):
        for requirement in queryset:
            generate_nurse_schedule(requirement.date)
        self.message_user(request, "✅ Schedule generated successfully.")

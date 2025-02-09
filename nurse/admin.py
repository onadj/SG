from django.contrib import admin
from django.http import HttpResponse
import csv
import pandas as pd
from django.apps import apps
from .models import Department, Role, ShiftType, Employee, ShiftRequirement, Shift, TimeOff, Day
from nurse.utils import generate_nurse_schedule
from django.utils.timezone import now
from datetime import timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

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
        total_hours = sum(shift.calculate_total_hours() for shift in last_week_shifts)
        return max(total_hours, 0.0)
    get_total_hours_last_week.short_description = "Total Hours Last 7 Days"

    def changelist_view(self, request, extra_context=None):
        Employee = apps.get_model('nurse', 'Employee')
        all_employees = Employee.objects.all()

        # ✅ Ukupni max weekly hours svih zaposlenika
        total_max_weekly_hours = sum(emp.max_weekly_hours for emp in all_employees)

        # ✅ Ukupni Total Hours Last 7 Days svih zaposlenika
        total_hours_last_week = sum(emp.get_total_hours_last_week() for emp in all_employees)

        # ✅ Dodaj statistiku u Django admin panel za Employees
        extra_context = extra_context or {}
        extra_context['summary_data'] = {
            "📊 Ukupni max weekly hours": total_max_weekly_hours,
            "📊 Ukupni Total Hours Last 7 Days": total_hours_last_week,
        }

        return super().changelist_view(request, extra_context=extra_context)

# === 📌 SHIFT ADMIN ===
@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = (
        'get_employee_full_name', 
        'department', 
        'get_role_name', 
        'date', 
        'start_time', 
        'end_time', 
        'corrected_total_hours', 
        'display_shift_configuration', 
        'display_missing_worker'
    )
    search_fields = ('employee__first_name', 'employee__last_name', 'department__name', 'role__name', 'date')
    list_filter = ('department', 'role', 'date', 'start_time', 'end_time')
    ordering = ('date', 'start_time')
    actions = ['export_schedule_to_csv', 'export_schedule_to_excel']

    def get_employee_full_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}" if obj.employee else "⚠️ Worker Missing"
    get_employee_full_name.short_description = "Employee"

    def get_role_name(self, obj):
        return obj.role.name if obj.role else "⚠️ Role Missing"
    get_role_name.short_description = "Role"

    def corrected_total_hours(self, obj):
        if obj.start_time > obj.end_time:
            total_seconds = ((24 - obj.start_time.hour) + obj.end_time.hour) * 3600 + (obj.end_time.minute - obj.start_time.minute) * 60
        else:
            total_seconds = (obj.end_time.hour * 3600 + obj.end_time.minute * 60) - (obj.start_time.hour * 3600 + obj.start_time.minute * 60)
        return round(total_seconds / 3600, 2)
    corrected_total_hours.short_description = "Total Hours"

    def display_shift_configuration(self, obj):
        Shift = apps.get_model('nurse', 'Shift')
        shifts_for_day = Shift.objects.filter(date=obj.date)
        total_hours = sum(shift.calculate_total_hours() for shift in shifts_for_day)
        return f"Total: {total_hours}h"
    display_shift_configuration.short_description = "Daily Shift Configuration"

    def display_missing_worker(self, obj):
        return "⚠️ Worker Needed" if obj.employee is None else "✅ Filled"
    display_missing_worker.short_description = "Shift Status"

    def changelist_view(self, request, extra_context=None):
        Shift = apps.get_model('nurse', 'Shift')
        Employee = apps.get_model('nurse', 'Employee')

        # ✅ Izračunaj ukupne sate u rasporedu
        total_shift_hours = sum(shift.calculate_total_hours() for shift in Shift.objects.all())

        # ✅ Izračunaj ukupan max weekly hours svih zaposlenika
        total_employee_max_hours = sum(emp.max_weekly_hours for emp in Employee.objects.all())

        # ✅ Izračunaj ukupan Total Hours Last 7 Days svih zaposlenika
        total_hours_last_week = sum(emp.get_total_hours_last_week() for emp in Employee.objects.all())

        # ✅ Dodaj ove vrijednosti u Django admin (da budu vidljive)
        extra_context = extra_context or {}
        extra_context['total_shift_hours'] = f"📊 Ukupni sati rasporeda: {total_shift_hours}"
        extra_context['total_employee_max_hours'] = f"📊 Ukupni max weekly hours: {total_employee_max_hours}"
        extra_context['total_hours_last_week'] = f"📊 Ukupni Total Hours Last 7 Days: {total_hours_last_week}"

        return super().changelist_view(request, extra_context=extra_context)

    @admin.action(description="📄 Export schedule to CSV")
    def export_schedule_to_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="shifts.csv"'
        writer = csv.writer(response)
        writer.writerow(["Employee", "Department", "Role", "Date", "Start Time", "End Time", "Total Hours"])
        for shift in queryset:
            writer.writerow([
                shift.get_employee_full_name(), 
                shift.department, 
                shift.get_role_name(), 
                shift.date, 
                shift.start_time, 
                shift.end_time, 
                shift.corrected_total_hours()
            ])
        return response

    @admin.action(description="📊 Export schedule to Excel")
    def export_schedule_to_excel(self, request, queryset):
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="shifts.xlsx"'
        df = pd.DataFrame([
            [
                shift.get_employee_full_name(), 
                shift.department, 
                shift.get_role_name(), 
                shift.date, 
                shift.start_time, 
                shift.end_time, 
                shift.corrected_total_hours()
            ]
            for shift in queryset
        ], columns=["Employee", "Department", "Role", "Date", "Start Time", "End Time", "Total Hours"])
        df.to_excel(response, index=False)
        return response


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

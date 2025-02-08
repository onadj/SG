from django.contrib import admin
from django.http import HttpResponse
import csv
import pandas as pd
from django.apps import apps
from .models import Department, Role, ShiftType, Employee, ShiftRequirement, Shift, TimeOff, Day
from nurse.utils import generate_nurse_schedule  # Uvoz skripte za generiranje rasporeda

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
    list_display = ('get_full_name', 'get_departments', 'get_roles', 'max_weekly_hours', 'max_daily_hours', 'priority')
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

# === 📌 SHIFT ADMIN ===
@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('get_employee_full_name', 'department', 'get_role_name', 'date', 'start_time', 'end_time', 'calculate_total_hours')
    search_fields = ('employee__first_name', 'employee__last_name', 'department__name', 'role__name', 'date')
    list_filter = ('department', 'role', 'date')
    ordering = ('date', 'start_time')
    actions = ['export_schedule_to_csv', 'export_schedule_to_excel', 'delete_all_shifts']

    def get_employee_full_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"
    get_employee_full_name.short_description = "Employee"

    def get_role_name(self, obj):
        return obj.role.name
    get_role_name.short_description = "Role"

    def calculate_total_hours(self, obj):
        return obj.calculate_total_hours()
    calculate_total_hours.short_description = "Total Hours"

    @admin.action(description="📄 Export schedule to CSV")
    def export_schedule_to_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="schedule.csv"'
        writer = csv.writer(response)
        writer.writerow(['Employee', 'Department', 'Role', 'Date', 'Start Time', 'End Time', 'Total Hours'])

        for shift in queryset.distinct():
            writer.writerow([
                self.get_employee_full_name(shift),
                shift.department.name, 
                shift.role.name, 
                shift.date, 
                shift.start_time.strftime('%H:%M'), 
                shift.end_time.strftime('%H:%M'), 
                self.calculate_total_hours(shift)
            ])
        return response

    @admin.action(description="📊 Export schedule to Excel")
    def export_schedule_to_excel(self, request, queryset):
        df = pd.DataFrame([
            (
                self.get_employee_full_name(shift),
                shift.department.name, 
                shift.role.name, 
                shift.date, 
                shift.start_time.strftime('%H:%M'), 
                shift.end_time.strftime('%H:%M'), 
                self.calculate_total_hours(shift)
            ) for shift in queryset.distinct()
        ], columns=['Employee', 'Department', 'Role', 'Date', 'Start Time', 'End Time', 'Total Hours'])

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="schedule.xlsx"'
        df.to_excel(response, index=False)
        return response

    @admin.action(description="🗑 Delete all shifts")
    def delete_all_shifts(self, request, queryset):
        queryset.delete()
        self.message_user(request, "🗑 All selected shifts have been deleted.")

# === 📌 TIME OFF ADMIN ===
@admin.register(TimeOff)
class TimeOffAdmin(admin.ModelAdmin):
    list_display = ('get_employee_full_name', 'start_date', 'end_date', 'reason')
    search_fields = ('employee__first_name', 'employee__last_name', 'reason')
    list_filter = ('reason', 'start_date', 'end_date')
    ordering = ('start_date', 'employee')

    def get_employee_full_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"
    get_employee_full_name.short_description = "Employee"

# === 📌 DAY ADMIN ===
@admin.register(Day)
class DayAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

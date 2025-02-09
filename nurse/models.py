from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse

DAYS_OF_WEEK = [
    ('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
    ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'), ('Sunday', 'Sunday')
]

# === DEPARTMENT ===
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name

# === ROLE ===
class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.department.name})"

# === SHIFT TYPE ===
class ShiftType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_hours = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"

from django.utils.timezone import now
from datetime import timedelta
from django.apps import apps

# === EMPLOYEE MODEL ===
class Employee(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    departments = models.ManyToManyField(Department)
    roles = models.ManyToManyField(Role)
    max_weekly_hours = models.PositiveIntegerField()
    max_daily_hours = models.PositiveIntegerField()
    available_days = models.ManyToManyField('Day', blank=True)
    can_work_shifts = models.ManyToManyField(ShiftType, blank=True)
    priority = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_total_hours_last_week(self):
        """Izračunava koliko je sati radnik odradio u zadnjih 7 dana."""
        Shift = apps.get_model('nurse', 'Shift')  # Dinamički uvoz Shift modela
        last_week_shifts = Shift.objects.filter(employee=self, date__gte=now().date() - timedelta(days=7))
        total_hours = sum(shift.calculate_total_hours() for shift in last_week_shifts)
        return max(total_hours, 0.0)

    get_total_hours_last_week.short_description = "Total Hours Last 7 Days"


# === DAY ===
class Day(models.Model):
    name = models.CharField(max_length=20, choices=DAYS_OF_WEEK, unique=True)
    
    def __str__(self):
        return self.name

# === SHIFT REQUIREMENT ===
class ShiftRequirement(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    date = models.DateField()
    shift_types = models.ManyToManyField(ShiftType)
    required_hours = models.PositiveIntegerField()
    required_roles = models.ManyToManyField(Role)

    def __str__(self):
        return f"{self.department.name} - {self.date} (Total: {self.required_hours}h)"

class Shift(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    def calculate_total_hours(self):
        start_seconds = self.start_time.hour * 3600 + self.start_time.minute * 60
        end_seconds = self.end_time.hour * 3600 + self.end_time.minute * 60

        if end_seconds < start_seconds:
            total_seconds = (24 * 3600 - start_seconds) + end_seconds
        else:
            total_seconds = end_seconds - start_seconds

        return round(total_seconds / 3600, 2)

    def get_admin_edit_url(self):
        """Vrati URL za editiranje ove smjene u Django adminu."""
        return reverse("admin:nurse_shift_change", args=[self.id])

    def __str__(self):
        return f"{self.employee} - {self.date} {self.start_time} - {self.end_time}"

# === TIME OFF ===
class TimeOff(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255, choices=[('sick', 'Sick'), ('holiday', 'Holiday')])
    
    def __str__(self):
        return f"{self.employee.first_name} {self.employee.last_name} - {self.reason} ({self.start_date} to {self.end_date})"
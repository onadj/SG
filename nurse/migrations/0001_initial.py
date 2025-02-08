# Generated by Django 5.1.6 on 2025-02-08 17:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Day',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(choices=[('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'), ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'), ('Sunday', 'Sunday')], max_length=20, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='ShiftType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('duration_hours', models.PositiveIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nurse.department')),
            ],
        ),
        migrations.CreateModel(
            name='Employee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('max_weekly_hours', models.PositiveIntegerField()),
                ('max_daily_hours', models.PositiveIntegerField()),
                ('priority', models.IntegerField(default=1)),
                ('available_days', models.ManyToManyField(blank=True, to='nurse.day')),
                ('departments', models.ManyToManyField(to='nurse.department')),
                ('roles', models.ManyToManyField(to='nurse.role')),
                ('can_work_shifts', models.ManyToManyField(blank=True, to='nurse.shifttype')),
            ],
        ),
        migrations.CreateModel(
            name='Shift',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nurse.department')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nurse.employee')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nurse.role')),
            ],
        ),
        migrations.CreateModel(
            name='ShiftRequirement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('required_hours', models.PositiveIntegerField()),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nurse.department')),
                ('required_roles', models.ManyToManyField(to='nurse.role')),
                ('shift_types', models.ManyToManyField(to='nurse.shifttype')),
            ],
        ),
        migrations.CreateModel(
            name='TimeOff',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('reason', models.CharField(choices=[('sick', 'Sick'), ('holiday', 'Holiday')], max_length=255)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nurse.employee')),
            ],
        ),
    ]

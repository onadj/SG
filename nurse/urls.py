from django.urls import path
from .views import nurse_schedule, generate_schedule, export_schedule_csv, export_schedule_excel, delete_shift, edit_shift

urlpatterns = [
    path('schedule/', nurse_schedule, name='nurse_schedule'),
    path('schedule/generate/', generate_schedule, name='generate_schedule'),
    path('schedule/export/csv/', export_schedule_csv, name='export_schedule_csv'),
    path('schedule/export/excel/', export_schedule_excel, name='export_schedule_excel'),
        path('schedule/delete/<int:shift_id>/', delete_shift, name='delete_shift'),
    path('schedule/edit/<int:shift_id>/', edit_shift, name='edit_shift'),
]


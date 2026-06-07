from django.contrib import admin

from .models import Habit


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "archived", "created_at")
    list_filter = ("archived", "created_at")
    search_fields = ("name", "user__email")
    ordering = ("-created_at",)

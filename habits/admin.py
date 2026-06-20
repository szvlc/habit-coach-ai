from django.contrib import admin

from .models import Habit, HabitExecution, Recommendation


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "archived", "created_at")
    list_filter = ("archived", "created_at")
    search_fields = ("name", "user__email")
    ordering = ("-created_at",)


@admin.register(HabitExecution)
class HabitExecutionAdmin(admin.ModelAdmin):
    list_display = ("habit", "date", "created_at")
    list_filter = ("date",)
    search_fields = ("habit__name", "habit__user__email")
    ordering = ("-date",)


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("user", "model_used", "grounded", "created_at")
    list_filter = ("grounded", "model_used", "created_at")
    search_fields = ("user__email", "text")
    ordering = ("-created_at",)

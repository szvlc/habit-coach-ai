from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from .forms import HabitForm
from .models import Habit, HabitExecution

HISTORY_DAYS = 30


class HabitCreateView(LoginRequiredMixin, CreateView):
    form_class = HabitForm
    template_name = "habits/habit_form.html"
    success_url = reverse_lazy("accounts:dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class HabitUpdateView(LoginRequiredMixin, UpdateView):
    form_class = HabitForm
    template_name = "habits/habit_form.html"
    success_url = reverse_lazy("accounts:dashboard")

    def get_queryset(self):
        return Habit.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class HabitArchiveView(LoginRequiredMixin, View):
    template_name = "habits/habit_confirm_archive.html"

    def get(self, request, pk):
        habit = get_object_or_404(Habit, pk=pk, user=request.user)
        return render(request, self.template_name, {"habit": habit})

    def post(self, request, pk):
        habit = get_object_or_404(Habit, pk=pk, user=request.user)
        habit.archived = True
        habit.save(update_fields=["archived"])
        return redirect("accounts:dashboard")


class HabitToggleView(LoginRequiredMixin, View):
    """Toggle today's execution for one habit. No backdating by construction:
    the only mutating endpoint always operates on timezone.localdate()."""

    def post(self, request, pk):
        habit = get_object_or_404(Habit, pk=pk, user=request.user, archived=False)
        today = timezone.localdate()
        execution = HabitExecution.objects.filter(habit=habit, date=today).first()
        if execution is not None:
            execution.delete()
            done = False
        else:
            HabitExecution.objects.create(habit=habit, date=today)
            done = True
        if request.headers.get("HX-Request"):
            return render(
                request, "habits/_toggle_button.html", {"habit": habit, "done": done}
            )
        return redirect("accounts:dashboard")


class HabitHistoryView(LoginRequiredMixin, TemplateView):
    template_name = "habits/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()
        start = today - timedelta(days=HISTORY_DAYS - 1)
        days = [start + timedelta(days=offset) for offset in range(HISTORY_DAYS)]
        habits = list(Habit.objects.active(user))
        done = set(
            HabitExecution.objects.history_for(user, start).values_list("habit_id", "date")
        )
        context["today"] = today
        context["days"] = days
        context["rows"] = [
            {
                "habit": habit,
                "cells": [{"date": day, "done": (habit.pk, day) in done} for day in days],
            }
            for habit in habits
        ]
        return context

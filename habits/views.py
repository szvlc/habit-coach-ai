import logging
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView
from openai import OpenAIError

from .forms import HabitForm
from .models import Habit, HabitExecution, Recommendation
from .recommendations import (
    HISTORY_DAYS,
    auto_recommendation_due,
    build_daily_completion,
    build_history_context,
    can_generate,
    generate_recommendation,
    is_grounded,
)

logger = logging.getLogger(__name__)


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


class HabitAnalyticsView(LoginRequiredMixin, TemplateView):
    """Server-rendered 30-day analytics (post-MVP): per-habit metric cards plus
    an aggregate daily-completion bar chart. Pure presentation over existing
    data — no new model, no JS/CDN dependency (see change habit-analytics)."""

    template_name = "habits/analytics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        history = build_history_context(user)
        context["habits"] = history["habits"]
        context["today"] = history["today"]
        context["daily"] = build_daily_completion(user)
        context["history_days"] = HISTORY_DAYS
        return context


class RecommendationGenerateView(LoginRequiredMixin, View):
    """Generate an on-demand AI recommendation (FR-011). Guards on data
    threshold, calls the OpenRouter service, persists with the observational
    grounding flag (Q2). On API error: friendly message, no row saved."""

    def post(self, request):
        if not can_generate(request.user):
            return self._render(
                request,
                error="Dodaj nawyk i zaloguj wykonanie, aby wygenerować rekomendację.",
            )
        try:
            text, model_used = generate_recommendation(request.user)
        except OpenAIError:
            # Only transient LLM/API failures degrade to a friendly message.
            # A programming error (bug in prompt/grounding/DB) is NOT swallowed —
            # it propagates so it surfaces instead of masquerading as "try again".
            logger.exception("OpenRouter recommendation generation failed")
            return self._render(
                request,
                error="Nie udało się wygenerować rekomendacji. Spróbuj ponownie.",
            )
        grounded = is_grounded(text, request.user)
        recommendation = Recommendation.objects.create(
            user=request.user, text=text, model_used=model_used, grounded=grounded
        )
        logger.info(
            "recommendation generated user=%s model=%s grounded=%s",
            request.user.pk,
            model_used,
            grounded,
        )
        return self._render(request, recommendation=recommendation)

    def _render(self, request, recommendation=None, error=None):
        context = {
            "recommendation": recommendation,
            "rec_error": error,
            "can_generate": can_generate(request.user),
        }
        if request.headers.get("HX-Request"):
            return render(request, "habits/_recommendation.html", context)
        return redirect("accounts:dashboard")


class RecommendationAutoView(LoginRequiredMixin, View):
    """Proactive recommendation (FR-013). Fired by the dashboard's lazy
    hx-trigger=load only when due. Generates once; silent on failure (no row,
    no banner) so the due-check stays True and retries on the next load."""

    def post(self, request):
        recommendation = Recommendation.objects.latest_for(request.user)
        if auto_recommendation_due(request.user):
            try:
                text, model_used = generate_recommendation(request.user)
                recommendation = Recommendation.objects.create(
                    user=request.user,
                    text=text,
                    model_used=model_used,
                    grounded=is_grounded(text, request.user),
                    proactive=True,
                )
                logger.info(
                    "proactive recommendation generated user=%s model=%s grounded=%s",
                    request.user.pk,
                    model_used,
                    recommendation.grounded,
                )
            except OpenAIError:
                # Silent on transient LLM/API failure (FR-013: no banner, retry
                # next load). Non-API exceptions (real bugs) are left to propagate
                # rather than being silently swallowed as "generation failed".
                logger.exception("proactive recommendation generation failed")
        return render(
            request,
            "habits/_recommendation.html",
            {"recommendation": recommendation, "can_generate": can_generate(request.user)},
        )

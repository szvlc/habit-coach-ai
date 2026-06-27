from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, TemplateView

from habits.models import Habit, HabitExecution, Recommendation
from habits.recommendations import auto_recommendation_due, can_generate

from .forms import CustomUserCreationForm


class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("accounts:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        habits = list(Habit.objects.active(self.request.user))
        done_ids = HabitExecution.objects.done_habit_ids_for(
            self.request.user, timezone.localdate()
        )
        for habit in habits:
            habit.done_today = habit.pk in done_ids
        context["habits"] = habits
        context["recommendation"] = Recommendation.objects.latest_for(self.request.user)
        context["can_generate"] = can_generate(self.request.user)
        context["should_auto_generate"] = auto_recommendation_due(self.request.user)
        return context

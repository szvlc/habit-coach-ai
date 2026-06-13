from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, UpdateView

from .forms import HabitForm
from .models import Habit


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

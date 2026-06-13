from django import forms

from .models import Habit


class HabitForm(forms.ModelForm):
    class Meta:
        model = Habit
        fields = ["name"]

    def clean_name(self):
        return self.cleaned_data["name"].strip()

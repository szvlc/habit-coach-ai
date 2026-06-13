from django import forms

from .models import Habit


class HabitForm(forms.ModelForm):
    class Meta:
        model = Habit
        fields = ["name"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # `user` is not a form field (it is set by the view), so ModelForm's
        # validate_unique() excludes it and cannot enforce the (user, name)
        # UniqueConstraint. We check it explicitly here for a friendly error;
        # the model constraint remains as the DB-level guarantee.
        self.user = user

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if self.user is not None:
            duplicates = Habit.objects.filter(user=self.user, name=name)
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise forms.ValidationError("Masz już nawyk o tej nazwie.")
        return name

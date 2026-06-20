from django.conf import settings
from django.db import models


class HabitManager(models.Manager):
    def active(self, user):
        return self.filter(user=user, archived=False).order_by("created_at")


class Habit(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habits",
    )
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = HabitManager()

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="unique_habit_name_per_user",
            ),
        ]

    def __str__(self):
        return self.name


class HabitExecutionManager(models.Manager):
    def done_habit_ids_for(self, user, on_date):
        return set(
            self.filter(habit__user=user, date=on_date).values_list("habit_id", flat=True)
        )

    def history_for(self, user, since_date):
        return self.filter(
            habit__user=user, habit__archived=False, date__gte=since_date
        )


class HabitExecution(models.Model):
    habit = models.ForeignKey(
        "habits.Habit",
        on_delete=models.CASCADE,
        related_name="executions",
    )
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    objects = HabitExecutionManager()

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["habit", "date"],
                name="unique_execution_per_habit_day",
            ),
        ]

    def __str__(self):
        return f"{self.habit.name} @ {self.date}"


class RecommendationManager(models.Manager):
    def latest_for(self, user):
        return self.filter(user=user).order_by("-created_at").first()


class Recommendation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recommendations",
    )
    text = models.TextField()
    model_used = models.CharField(max_length=100)
    grounded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = RecommendationManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Rec for {self.user} @ {self.created_at:%Y-%m-%d}"

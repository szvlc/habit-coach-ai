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

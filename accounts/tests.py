from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from habits.models import Habit, HabitExecution, Recommendation

User = get_user_model()

STRONG_PASSWORD = "ZQ4!yt8mxL2p"


@override_settings(SECURE_SSL_REDIRECT=False)
class RegisterViewTests(TestCase):
    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:register"),
            {"email": "new@example.com", "password1": STRONG_PASSWORD, "password2": STRONG_PASSWORD},
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.assertTrue(User.objects.filter(email="new@example.com").exists())
        # Session is authenticated after auto-login
        self.assertEqual(int(self.client.session["_auth_user_id"]), User.objects.get(email="new@example.com").pk)

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(email="existing@example.com", password=STRONG_PASSWORD)
        response = self.client.post(
            reverse("accounts:register"),
            {"email": "existing@example.com", "password1": STRONG_PASSWORD, "password2": STRONG_PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        # Form re-renders with email field error — assertion is language-agnostic
        self.assertTrue(response.context["form"].has_error("email"))
        self.assertEqual(User.objects.filter(email="existing@example.com").count(), 1)

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            reverse("accounts:register"),
            {"email": "weak@example.com", "password1": "abc", "password2": "abc"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="weak@example.com").exists())


@override_settings(SECURE_SSL_REDIRECT=False)
class LoginViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="login@example.com", password=STRONG_PASSWORD)

    def test_login_with_correct_password(self):
        response = self.client.post(
            reverse("login"),
            {"username": "login@example.com", "password": STRONG_PASSWORD},
        )
        # LOGIN_REDIRECT_URL is accounts:dashboard which resolves to /
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_login_with_wrong_password(self):
        response = self.client.post(
            reverse("login"),
            {"username": "login@example.com", "password": "wrongpassword"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)


@override_settings(SECURE_SSL_REDIRECT=False)
class DashboardViewTests(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("accounts:dashboard"))
        # LoginRequiredMixin redirects to LOGIN_URL with ?next=
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
        self.assertIn("next=", response.url)

    def test_dashboard_shows_users_active_habits(self):
        user = User.objects.create_user(email="dash@example.com", password=STRONG_PASSWORD)
        active = Habit.objects.create(user=user, name="Aktywny")
        Habit.objects.create(user=user, name="Zarchiwizowany", archived=True)
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:dashboard"))

        self.assertEqual(list(response.context["habits"]), [active])

    def test_dashboard_does_not_show_other_users_habits(self):
        user_a = User.objects.create_user(email="a@example.com", password=STRONG_PASSWORD)
        user_b = User.objects.create_user(email="b@example.com", password=STRONG_PASSWORD)
        habit_a = Habit.objects.create(user=user_a, name="Nawyk A")
        self.client.force_login(user_b)

        response = self.client.get(reverse("accounts:dashboard"))

        self.assertNotIn(habit_a, list(response.context["habits"]))

    def test_dashboard_marks_habit_done_today(self):
        user = User.objects.create_user(email="done@example.com", password=STRONG_PASSWORD)
        done = Habit.objects.create(user=user, name="Zrobiony")
        not_done = Habit.objects.create(user=user, name="Niezrobiony")
        HabitExecution.objects.create(habit=done, date=timezone.localdate())
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:dashboard"))

        flags = {h.name: h.done_today for h in response.context["habits"]}
        self.assertTrue(flags["Zrobiony"])
        self.assertFalse(flags["Niezrobiony"])

    def test_dashboard_shows_latest_recommendation_and_can_generate_flag(self):
        user = User.objects.create_user(email="rec@example.com", password=STRONG_PASSWORD)
        other = User.objects.create_user(email="other@example.com", password=STRONG_PASSWORD)
        habit = Habit.objects.create(user=user, name="Czytanie")
        HabitExecution.objects.create(habit=habit, date=timezone.localdate())
        Recommendation.objects.create(user=user, text="moja rekomendacja", model_used="m", grounded=True)
        Recommendation.objects.create(user=other, text="cudza rekomendacja", model_used="m", grounded=True)
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:dashboard"))

        self.assertEqual(response.context["recommendation"].text, "moja rekomendacja")
        self.assertTrue(response.context["can_generate"])

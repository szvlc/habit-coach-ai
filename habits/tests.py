from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Habit

User = get_user_model()

STRONG_PASSWORD = "ZQ4!yt8mxL2p"


@override_settings(SECURE_SSL_REDIRECT=False)
class HabitCreateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        self.client.force_login(self.user)

    def test_create_creates_habit_for_logged_in_user(self):
        response = self.client.post(reverse("habits:add"), {"name": "Czytanie"})
        self.assertRedirects(response, reverse("accounts:dashboard"))
        habit = Habit.objects.get(name="Czytanie")
        self.assertEqual(habit.user, self.user)
        self.assertFalse(habit.archived)

    def test_create_strips_whitespace_from_name(self):
        self.client.post(reverse("habits:add"), {"name": "  Bieganie  "})
        self.assertTrue(Habit.objects.filter(user=self.user, name="Bieganie").exists())

    def test_create_rejects_duplicate_name_for_same_user(self):
        Habit.objects.create(user=self.user, name="Czytanie")
        response = self.client.post(reverse("habits:add"), {"name": "Czytanie"})
        # Must be a friendly form error (200), NOT a 500 IntegrityError.
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].has_error("name"))
        self.assertEqual(Habit.objects.filter(user=self.user, name="Czytanie").count(), 1)

    def test_create_allows_duplicate_name_across_different_users(self):
        other = User.objects.create_user(email="other@example.com", password=STRONG_PASSWORD)
        Habit.objects.create(user=other, name="Czytanie")
        response = self.client.post(reverse("habits:add"), {"name": "Czytanie"})
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.assertTrue(Habit.objects.filter(user=self.user, name="Czytanie").exists())

    def test_create_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("habits:add"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)


@override_settings(SECURE_SSL_REDIRECT=False)
class HabitUpdateViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        self.other = User.objects.create_user(email="other@example.com", password=STRONG_PASSWORD)
        self.habit = Habit.objects.create(user=self.owner, name="Czytanie")
        self.client.force_login(self.owner)

    def test_update_changes_name_for_own_habit(self):
        response = self.client.post(
            reverse("habits:edit", args=[self.habit.pk]), {"name": "Czytanie książek"}
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.habit.refresh_from_db()
        self.assertEqual(self.habit.name, "Czytanie książek")

    def test_update_rejects_other_users_habit_with_404(self):
        self.client.force_login(self.other)
        url = reverse("habits:edit", args=[self.habit.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, {"name": "Hack"}).status_code, 404)
        self.habit.refresh_from_db()
        self.assertEqual(self.habit.name, "Czytanie")

    def test_update_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("habits:edit", args=[self.habit.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)


@override_settings(SECURE_SSL_REDIRECT=False)
class HabitArchiveViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        self.other = User.objects.create_user(email="other@example.com", password=STRONG_PASSWORD)
        self.habit = Habit.objects.create(user=self.owner, name="Czytanie")
        self.client.force_login(self.owner)

    def test_archive_get_shows_confirm_page_for_own_habit(self):
        response = self.client.get(reverse("habits:archive", args=[self.habit.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Czytanie")
        # GET must not mutate state.
        self.habit.refresh_from_db()
        self.assertFalse(self.habit.archived)

    def test_archive_post_sets_archived_true_and_redirects(self):
        response = self.client.post(reverse("habits:archive", args=[self.habit.pk]))
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.habit.refresh_from_db()
        self.assertTrue(self.habit.archived)

    def test_archive_rejects_other_users_habit_with_404(self):
        self.client.force_login(self.other)
        url = reverse("habits:archive", args=[self.habit.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.habit.refresh_from_db()
        self.assertFalse(self.habit.archived)

    def test_archive_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("habits:archive", args=[self.habit.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)


@override_settings(SECURE_SSL_REDIRECT=False)
class HabitManagerTests(TestCase):
    def test_active_returns_only_users_unarchived_habits(self):
        owner = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        other = User.objects.create_user(email="other@example.com", password=STRONG_PASSWORD)
        active = Habit.objects.create(user=owner, name="Aktywny")
        Habit.objects.create(user=owner, name="Zarchiwizowany", archived=True)
        Habit.objects.create(user=other, name="Cudzy")

        result = Habit.objects.active(owner)

        self.assertEqual(list(result), [active])

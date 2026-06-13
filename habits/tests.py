from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Habit, HabitExecution

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


@override_settings(SECURE_SSL_REDIRECT=False)
class HabitToggleViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        self.other = User.objects.create_user(email="other@example.com", password=STRONG_PASSWORD)
        self.habit = Habit.objects.create(user=self.owner, name="Czytanie")
        self.url = reverse("habits:toggle", args=[self.habit.pk])
        self.client.force_login(self.owner)

    def test_toggle_creates_execution_for_today(self):
        response = self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        execution = HabitExecution.objects.get(habit=self.habit)
        self.assertEqual(execution.date, timezone.localdate())

    def test_toggle_twice_removes_execution(self):
        self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.assertFalse(HabitExecution.objects.filter(habit=self.habit).exists())

    def test_toggle_htmx_returns_partial_with_new_state(self):
        done = self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.assertContains(done, "Zrobione dziś")
        undone = self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.assertContains(undone, "Oznacz wykonane")

    def test_toggle_without_htmx_redirects_to_dashboard(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.assertTrue(HabitExecution.objects.filter(habit=self.habit).exists())

    def test_toggle_rejects_other_users_habit_with_404(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 404)
        self.assertFalse(HabitExecution.objects.filter(habit=self.habit).exists())

    def test_toggle_rejects_archived_habit_with_404(self):
        archived = Habit.objects.create(user=self.owner, name="Stary", archived=True)
        url = reverse("habits:toggle", args=[archived.pk])
        response = self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 404)

    def test_toggle_requires_login(self):
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)


@override_settings(SECURE_SSL_REDIRECT=False)
class HabitExecutionModelTests(TestCase):
    def test_unique_constraint_blocks_duplicate_per_day(self):
        user = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        habit = Habit.objects.create(user=user, name="Czytanie")
        today = timezone.localdate()
        HabitExecution.objects.create(habit=habit, date=today)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                HabitExecution.objects.create(habit=habit, date=today)


@override_settings(SECURE_SSL_REDIRECT=False)
class HabitExecutionManagerTests(TestCase):
    def test_done_habit_ids_for_returns_only_users_executions_on_date(self):
        owner = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        other = User.objects.create_user(email="other@example.com", password=STRONG_PASSWORD)
        today = timezone.localdate()
        h_done = Habit.objects.create(user=owner, name="Done")
        h_not = Habit.objects.create(user=owner, name="NotDone")
        h_other = Habit.objects.create(user=other, name="Cudzy")
        HabitExecution.objects.create(habit=h_done, date=today)
        HabitExecution.objects.create(habit=h_other, date=today)

        ids = HabitExecution.objects.done_habit_ids_for(owner, today)

        self.assertEqual(ids, {h_done.pk})
        self.assertNotIn(h_not.pk, ids)
        self.assertNotIn(h_other.pk, ids)

    def test_history_for_excludes_archived_and_other_users_and_old(self):
        owner = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        other = User.objects.create_user(email="other@example.com", password=STRONG_PASSWORD)
        today = timezone.localdate()
        start = today - timedelta(days=29)
        active = Habit.objects.create(user=owner, name="Aktywny")
        archived = Habit.objects.create(user=owner, name="Zarchiwizowany", archived=True)
        cudzy = Habit.objects.create(user=other, name="Cudzy")
        in_window = HabitExecution.objects.create(habit=active, date=today)
        HabitExecution.objects.create(habit=active, date=start - timedelta(days=1))  # too old
        HabitExecution.objects.create(habit=archived, date=today)
        HabitExecution.objects.create(habit=cudzy, date=today)

        result = list(HabitExecution.objects.history_for(owner, start))

        self.assertEqual(result, [in_window])


@override_settings(SECURE_SSL_REDIRECT=False)
class HabitHistoryViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        self.url = reverse("habits:history")
        self.client.force_login(self.owner)

    def test_history_shows_grid_for_own_active_habits(self):
        habit = Habit.objects.create(user=self.owner, name="Czytanie")
        HabitExecution.objects.create(habit=habit, date=timezone.localdate())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["days"]), 30)
        names = [row["habit"].name for row in response.context["rows"]]
        self.assertIn("Czytanie", names)
        done_today = response.context["rows"][0]["cells"][-1]
        self.assertTrue(done_today["done"])

    def test_history_excludes_archived_habits(self):
        Habit.objects.create(user=self.owner, name="Aktywny")
        Habit.objects.create(user=self.owner, name="Zarchiwizowany", archived=True)
        response = self.client.get(self.url)
        names = [row["habit"].name for row in response.context["rows"]]
        self.assertIn("Aktywny", names)
        self.assertNotIn("Zarchiwizowany", names)

    def test_history_excludes_other_users_habits(self):
        other = User.objects.create_user(email="other@example.com", password=STRONG_PASSWORD)
        Habit.objects.create(user=other, name="Cudzy")
        Habit.objects.create(user=self.owner, name="Mój")
        response = self.client.get(self.url)
        names = [row["habit"].name for row in response.context["rows"]]
        self.assertEqual(names, ["Mój"])

    def test_history_empty_state_when_no_habits(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["rows"], [])
        self.assertContains(response, "Dodaj swój pierwszy nawyk")

    def test_history_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

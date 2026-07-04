from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import recommendations
from .models import Habit, HabitExecution, Recommendation

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


@override_settings(SECURE_SSL_REDIRECT=False)
class RecommendationContextTests(TestCase):
    def test_context_signals_and_active_only(self):
        user = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        today = timezone.localdate()
        habit = Habit.objects.create(user=user, name="Czytanie")
        Habit.objects.create(user=user, name="Zarchiwizowany", archived=True)
        for off in (0, 1, 2):  # streak of 3 up to today
            HabitExecution.objects.create(habit=habit, date=today - timedelta(days=off))

        ctx = recommendations.build_history_context(user)

        self.assertEqual(len(ctx["days"]), recommendations.HISTORY_DAYS)
        names = [h["name"] for h in ctx["habits"]]
        self.assertEqual(names, ["Czytanie"])  # archived excluded
        row = ctx["habits"][0]
        self.assertEqual(row["current_streak"], 3)
        self.assertEqual(row["done_count"], 3)

    def test_context_isolation_excludes_other_users(self):
        a = User.objects.create_user(email="a@example.com", password=STRONG_PASSWORD)
        b = User.objects.create_user(email="b@example.com", password=STRONG_PASSWORD)
        Habit.objects.create(user=a, name="NawykA")
        Habit.objects.create(user=b, name="NawykB")

        ctx = recommendations.build_history_context(a)

        names = [h["name"] for h in ctx["habits"]]
        self.assertEqual(names, ["NawykA"])
        self.assertNotIn("NawykB", names)

    def test_context_weakest_weekday_none_when_fully_complete(self):
        user = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        today = timezone.localdate()
        habit = Habit.objects.create(user=user, name="Codzienny")
        for off in range(recommendations.HISTORY_DAYS):
            HabitExecution.objects.create(habit=habit, date=today - timedelta(days=off))

        row = recommendations.build_history_context(user)["habits"][0]

        self.assertEqual(row["completion_rate"], 100)
        self.assertIsNone(row["weakest_weekday"])


@override_settings(SECURE_SSL_REDIRECT=False)
class IsGroundedTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        Habit.objects.create(user=self.user, name="Czytanie")

    def test_grounded_true_when_habit_name_present(self):
        self.assertTrue(recommendations.is_grounded("Twój nawyk Czytanie idzie świetnie", self.user))

    def test_grounded_false_for_generic_text(self):
        self.assertFalse(recommendations.is_grounded("Pij więcej wody i śpij 8 godzin", self.user))


@override_settings(SECURE_SSL_REDIRECT=False)
class RecommendationGenerateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        self.url = reverse("habits:recommend")
        self.client.force_login(self.user)

    def _seed_data(self):
        habit = Habit.objects.create(user=self.user, name="Czytanie")
        HabitExecution.objects.create(habit=habit, date=timezone.localdate())
        return habit

    def test_generate_creates_recommendation_and_shows_text(self):
        self._seed_data()
        with patch(
            "habits.views.generate_recommendation",
            return_value=("Twoje Czytanie ma dobry streak.", "anthropic/claude-haiku-4-5"),
        ):
            response = self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        rec = Recommendation.objects.get(user=self.user)
        self.assertEqual(rec.model_used, "anthropic/claude-haiku-4-5")
        self.assertContains(response, "Czytanie")

    def test_generated_recommendation_grounded_flag_set(self):
        self._seed_data()
        with patch(
            "habits.views.generate_recommendation",
            return_value=("Czytanie idzie świetnie!", "anthropic/claude-haiku-4-5"),
        ):
            self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.assertTrue(Recommendation.objects.get(user=self.user).grounded)

    def test_generate_blocked_without_data(self):
        with patch("habits.views.generate_recommendation") as gen:
            response = self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.assertFalse(gen.called)
        self.assertEqual(Recommendation.objects.filter(user=self.user).count(), 0)
        self.assertContains(response, "Dodaj nawyk")

    def test_generate_api_error_shows_message_no_save(self):
        self._seed_data()
        with patch("habits.views.generate_recommendation", side_effect=RuntimeError("boom")):
            response = self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Recommendation.objects.filter(user=self.user).count(), 0)
        self.assertContains(response, "Nie udało się")

    def test_generate_uses_only_request_user_data(self):
        self._seed_data()
        with patch(
            "habits.views.generate_recommendation",
            return_value=("ok", "m"),
        ) as gen:
            self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.assertEqual(gen.call_args.args[0], self.user)

    def test_generate_requires_login(self):
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)


@override_settings(SECURE_SSL_REDIRECT=False)
class RecommendationModelTests(TestCase):
    def test_latest_for_returns_users_most_recent_not_others(self):
        a = User.objects.create_user(email="a@example.com", password=STRONG_PASSWORD)
        b = User.objects.create_user(email="b@example.com", password=STRONG_PASSWORD)
        Recommendation.objects.create(user=a, text="stara", model_used="m", grounded=True)
        newest = Recommendation.objects.create(user=a, text="nowa", model_used="m", grounded=True)
        Recommendation.objects.create(user=b, text="cudza", model_used="m", grounded=True)

        result = Recommendation.objects.latest_for(a)

        self.assertEqual(result, newest)


@override_settings(SECURE_SSL_REDIRECT=False)
class RecommendationServiceTests(TestCase):
    def test_generate_passes_model_max_tokens_and_timeout(self):
        from unittest.mock import MagicMock

        user = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        habit = Habit.objects.create(user=user, name="Czytanie")
        HabitExecution.objects.create(habit=habit, date=timezone.localdate())

        with patch("habits.recommendations.OpenAI") as MockOpenAI:
            client = MockOpenAI.return_value
            msg = MagicMock()
            msg.content = "Czytanie idzie świetnie."
            client.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=msg)]
            )
            text, model = recommendations.generate_recommendation(user)

        kwargs = client.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "anthropic/claude-haiku-4.5")
        self.assertEqual(kwargs["max_tokens"], 500)
        self.assertEqual(kwargs["timeout"], 9.0)
        self.assertEqual(text, "Czytanie idzie świetnie.")


@override_settings(SECURE_SSL_REDIRECT=False)
class AutoRecommendationDueTests(TestCase):
    def _log_days(self, user, n):
        habit = Habit.objects.create(user=user, name="Czytanie")
        today = timezone.localdate()
        for d in range(n):
            HabitExecution.objects.create(habit=habit, date=today - timedelta(days=d))
        return habit

    def test_below_threshold_not_due(self):
        user = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        self._log_days(user, 6)
        self.assertEqual(recommendations.logged_day_count(user), 6)
        self.assertFalse(recommendations.auto_recommendation_due(user))

    def test_at_threshold_due(self):
        user = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        self._log_days(user, 7)
        self.assertTrue(recommendations.auto_recommendation_due(user))

    def test_not_due_after_proactive_exists(self):
        user = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        self._log_days(user, 7)
        Recommendation.objects.create(user=user, text="x", model_used="m", proactive=True)
        self.assertFalse(recommendations.auto_recommendation_due(user))

    def test_threshold_is_per_user(self):
        a = User.objects.create_user(email="a@example.com", password=STRONG_PASSWORD)
        b = User.objects.create_user(email="b@example.com", password=STRONG_PASSWORD)
        self._log_days(a, 3)
        self._log_days(b, 10)
        self.assertEqual(recommendations.logged_day_count(a), 3)
        self.assertFalse(recommendations.auto_recommendation_due(a))


@override_settings(SECURE_SSL_REDIRECT=False)
class RecommendationAutoViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        self.url = reverse("habits:recommend_auto")
        self.client.force_login(self.user)

    def _reach_threshold(self):
        habit = Habit.objects.create(user=self.user, name="Czytanie")
        today = timezone.localdate()
        for d in range(7):
            HabitExecution.objects.create(habit=habit, date=today - timedelta(days=d))

    def test_auto_generates_proactive_recommendation_when_due(self):
        self._reach_threshold()
        with patch(
            "habits.views.generate_recommendation",
            return_value=("Twoje Czytanie ma streak.", "anthropic/claude-haiku-4.5"),
        ):
            response = self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        rec = Recommendation.objects.get(user=self.user)
        self.assertTrue(rec.proactive)
        self.assertContains(response, "Automatyczna")
        self.assertContains(response, "Czytanie")

    def test_auto_noop_when_not_due(self):
        # only 3 logged days -> not due
        habit = Habit.objects.create(user=self.user, name="Czytanie")
        today = timezone.localdate()
        for d in range(3):
            HabitExecution.objects.create(habit=habit, date=today - timedelta(days=d))
        with patch("habits.views.generate_recommendation") as gen:
            response = self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(gen.called)
        self.assertEqual(Recommendation.objects.filter(user=self.user).count(), 0)

    def test_auto_one_time_after_success(self):
        self._reach_threshold()
        with patch(
            "habits.views.generate_recommendation",
            return_value=("Czytanie ok", "m"),
        ):
            self.client.post(self.url, HTTP_HX_REQUEST="true")
        # second call must NOT generate again
        with patch("habits.views.generate_recommendation", side_effect=AssertionError("called again")):
            self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.assertEqual(Recommendation.objects.filter(user=self.user).count(), 1)

    def test_auto_silent_on_error(self):
        self._reach_threshold()
        with patch("habits.views.generate_recommendation", side_effect=RuntimeError("boom")):
            response = self.client.post(self.url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Recommendation.objects.filter(user=self.user).count(), 0)
        self.assertTrue(recommendations.auto_recommendation_due(self.user))

    def test_auto_requires_login(self):
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)


@override_settings(SECURE_SSL_REDIRECT=False)
class HabitAnalyticsViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password=STRONG_PASSWORD)
        self.url = reverse("habits:analytics")

    def test_analytics_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_analytics_shows_only_own_habits(self):
        other = User.objects.create_user(email="other@example.com", password=STRONG_PASSWORD)
        Habit.objects.create(user=self.owner, name="MojNawyk")
        Habit.objects.create(user=other, name="CudzyNawyk")
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertContains(response, "MojNawyk")
        self.assertNotContains(response, "CudzyNawyk")

    def test_analytics_metrics_reflect_executions(self):
        habit = Habit.objects.create(user=self.owner, name="Bieganie")
        today = timezone.localdate()
        HabitExecution.objects.create(habit=habit, date=today)
        HabitExecution.objects.create(habit=habit, date=today - timedelta(days=1))
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        row = next(h for h in response.context["habits"] if h["name"] == "Bieganie")
        self.assertEqual(row["current_streak"], 2)
        self.assertEqual(row["done_count"], 2)

    def test_analytics_empty_state_when_no_habits(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertContains(response, "Brak danych")

    def test_dashboard_has_analytics_link(self):
        Habit.objects.create(user=self.owner, name="X")  # link row renders only with habits
        self.client.force_login(self.owner)
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertContains(response, reverse("habits:analytics"))


@override_settings(SECURE_SSL_REDIRECT=False)
class BuildDailyCompletionTests(TestCase):
    def test_daily_completion_counts_only_own_active_habits(self):
        owner = User.objects.create_user(email="o@example.com", password=STRONG_PASSWORD)
        other = User.objects.create_user(email="ot@example.com", password=STRONG_PASSWORD)
        today = timezone.localdate()
        h1 = Habit.objects.create(user=owner, name="A")
        h2 = Habit.objects.create(user=owner, name="B")
        archived = Habit.objects.create(user=owner, name="Arch", archived=True)
        other_habit = Habit.objects.create(user=other, name="C")
        HabitExecution.objects.create(habit=h1, date=today)
        HabitExecution.objects.create(habit=h2, date=today)
        HabitExecution.objects.create(habit=archived, date=today)   # archived -> excluded
        HabitExecution.objects.create(habit=other_habit, date=today)  # other user -> excluded

        daily = recommendations.build_daily_completion(owner)

        self.assertEqual(len(daily), 30)
        latest = daily[-1]
        self.assertEqual(latest["date"], today)
        self.assertEqual(latest["total"], 2)        # only owner's active habits
        self.assertEqual(latest["done_count"], 2)   # h1 + h2 (not archived / other user)
        self.assertEqual(latest["pct"], 100)

from django.urls import path

from . import views

app_name = "habits"

urlpatterns = [
    path("add/", views.HabitCreateView.as_view(), name="add"),
    path("<int:pk>/edit/", views.HabitUpdateView.as_view(), name="edit"),
    path("<int:pk>/archive/", views.HabitArchiveView.as_view(), name="archive"),
    path("<int:pk>/toggle/", views.HabitToggleView.as_view(), name="toggle"),
    path("history/", views.HabitHistoryView.as_view(), name="history"),
    path("recommendation/generate/", views.RecommendationGenerateView.as_view(), name="recommend"),
]

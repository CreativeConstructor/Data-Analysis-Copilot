from django.urls import path
from .views import AnalyzeView, ConversationDetailView, DatasetDetailView, DatasetListCreateView, csrf, logout

urlpatterns = [
    path("csrf/", csrf), path("logout/", logout), path("datasets/", DatasetListCreateView.as_view()),
    path("datasets/<uuid:pk>/", DatasetDetailView.as_view()),
    path("analysis/", AnalyzeView.as_view()),
    path("conversations/<uuid:pk>/", ConversationDetailView.as_view()),
]

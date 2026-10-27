from django.urls import path
from .views import DatasetDetailView, DatasetListCreateView, csrf, logout

urlpatterns = [
    path("csrf/", csrf), path("logout/", logout), path("datasets/", DatasetListCreateView.as_view()),
    path("datasets/<uuid:pk>/", DatasetDetailView.as_view()),
]

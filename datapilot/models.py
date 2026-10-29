import uuid
from django.conf import settings
from django.db import models
from pgvector.django import VectorField

class Dataset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="datasets")
    original_filename = models.CharField(max_length=255)
    storage_path = models.CharField(max_length=500)
    row_count = models.PositiveIntegerField()
    column_count = models.PositiveIntegerField()
    profile = models.JSONField(default=dict)
    deleting = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class ColumnSchema(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="schema_documents")
    column_name = models.CharField(max_length=255)
    data_type = models.CharField(max_length=100)
    searchable_text = models.CharField(max_length=1200)
    embedding = VectorField(dimensions=settings.GEMINI_EMBEDDING_DIMENSIONS, null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("dataset", "column_name"), name="unique_dataset_column_schema")]


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="analysis_conversations")
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)


class Turn(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="turns")
    question = models.TextField(max_length=2000)
    code = models.TextField(blank=True)
    status = models.CharField(max_length=20, default="pending")
    insight = models.TextField(blank=True)
    chart = models.JSONField(null=True, blank=True)
    table = models.JSONField(null=True, blank=True)
    attempts = models.JSONField(default=list)
    error = models.CharField(max_length=300, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

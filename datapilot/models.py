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

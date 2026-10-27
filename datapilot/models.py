import uuid
from django.conf import settings
from django.db import models

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

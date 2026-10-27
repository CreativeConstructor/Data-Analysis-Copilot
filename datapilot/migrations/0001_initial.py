import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name="Dataset", fields=[("id", models.UUIDField(primary_key=True, default=uuid.uuid4, serialize=False, editable=False)), ("original_filename", models.CharField(max_length=255)), ("storage_path", models.CharField(max_length=500)), ("row_count", models.PositiveIntegerField()), ("column_count", models.PositiveIntegerField()), ("profile", models.JSONField(default=dict)), ("deleting", models.BooleanField(default=False)), ("created_at", models.DateTimeField(auto_now_add=True)), ("owner", models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.CASCADE, related_name="datasets"))])]

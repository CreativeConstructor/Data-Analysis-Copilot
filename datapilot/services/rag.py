"""Privacy-filtered schema embeddings and dataset-scoped pgvector retrieval."""
import logging
import math
import os

from django.conf import settings
from pgvector.django import CosineDistance

from ..models import ColumnSchema
from .privacy import privacy_filtered_profile, sanitize_text

logger = logging.getLogger(__name__)


class EmbeddingFailure(Exception):
    """Safe error raised when Gemini cannot produce a valid embedding."""


def embed_text(text, *, task_type):
    """Embed bounded schema/question text using the configured Gemini model."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EmbeddingFailure("Gemini API key is not configured.")
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=settings.GEMINI_REQUEST_TIMEOUT_SECONDS * 1000
            ),
        )
        response = client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.GEMINI_EMBEDDING_DIMENSIONS,
            ),
        )
        embeddings = getattr(response, "embeddings", None) or []
        values = list(embeddings[0].values) if embeddings else []
        if len(values) != settings.GEMINI_EMBEDDING_DIMENSIONS:
            raise EmbeddingFailure("Gemini returned an embedding with an unexpected size.")
        if not all(math.isfinite(float(value)) for value in values):
            raise EmbeddingFailure("Gemini returned an invalid embedding.")
        return [float(value) for value in values]
    except EmbeddingFailure:
        raise
    except Exception as exc:
        # Exception messages from remote SDKs may contain request details.
        raise EmbeddingFailure(f"Gemini embedding request failed ({type(exc).__name__}).") from None


def _column_text(dataset, column):
    name = sanitize_text(column.get("name", "Unnamed column"))[:255]
    data_type = sanitize_text(column.get("type", "unknown"))[:100]
    parts = [f"Column: {name}", f"Type: {data_type}", f"Dataset rows: {dataset.row_count}"]
    stats = column.get("statistics", {})
    if stats:
        safe_stats = {sanitize_text(key)[:32]: value for key, value in list(stats.items())[:4]}
        parts.append(f"Numeric profile: {safe_stats}")
    parts.append(f"Missing values: {column.get('missing_count', 0)}")
    parts.append(f"Distinct values: {column.get('distinct_count', 0)}")
    samples = column.get("samples", [])
    if samples:
        parts.append("Example values: " + ", ".join(sanitize_text(value)[:80] for value in samples[:3]))
    return " | ".join(parts)[:1200]


def index_dataset(dataset):
    """Idempotently upsert one privacy-filtered embedding per dataset column."""
    safe_profile = privacy_filtered_profile(dataset.profile or {})
    columns = safe_profile.get("profile", [])
    existing = {
        item.column_name: item
        for item in ColumnSchema.objects.filter(dataset=dataset)
    }
    documents = []
    names = []
    embedding_available = True
    for column in columns:
        name = sanitize_text(column.get("name", ""))[:255]
        if not name:
            continue
        names.append(name)
        text = _column_text(dataset, column)
        old = existing.get(name)
        if old and old.searchable_text == text and old.embedding is not None:
            continue
        vector = None
        if embedding_available:
            try:
                vector = embed_text(text, task_type="RETRIEVAL_DOCUMENT")
            except EmbeddingFailure as exc:
                embedding_available = False
                logger.warning("Schema embeddings unavailable for dataset %s: %s", dataset.pk, exc)
        documents.append(ColumnSchema(
            dataset=dataset,
            column_name=name,
            data_type=sanitize_text(column.get("type", "unknown"))[:100],
            searchable_text=text,
            embedding=vector,
        ))

    if documents:
        ColumnSchema.objects.bulk_create(
            documents,
            update_conflicts=True,
            update_fields=["data_type", "searchable_text", "embedding"],
            unique_fields=["dataset", "column_name"],
        )
    ColumnSchema.objects.filter(dataset=dataset).exclude(column_name__in=names).delete()
    return len(columns)


def _full_schema(dataset):
    import json

    return json.dumps(privacy_filtered_profile(dataset.profile or {}), ensure_ascii=False)[:settings.DATASET_MAX_SCHEMA_CHARS]


def build_schema_context(dataset, question):
    """Return full schema or RAG-selected columns, scoped to this dataset."""
    full_schema = _full_schema(dataset)
    if dataset.column_count <= settings.DATASET_RAG_COLUMN_THRESHOLD:
        return full_schema
    try:
        query_embedding = embed_text(sanitize_text(question)[:2000], task_type="RETRIEVAL_QUERY")
        top_k = min(50, max(1, int(settings.ANALYSIS_RAG_TOP_K)))
        matches = list(
            ColumnSchema.objects.filter(dataset=dataset, embedding__isnull=False)
            .annotate(distance=CosineDistance("embedding", query_embedding))
            .order_by("distance")[:top_k]
        )
        max_distance = float(settings.ANALYSIS_RAG_MAX_COSINE_DISTANCE)
        useful = [item for item in matches if item.distance is not None and item.distance <= max_distance]
        if not useful:
            logger.warning("No useful schema matches for dataset %s; using full schema.", dataset.pk)
            return full_schema
        selected_profile = {
            "rows": dataset.row_count,
            "columns": len(useful),
            "profile": [
                {"name": item.column_name, "type": item.data_type,
                 "searchable_text": item.searchable_text}
                for item in useful
            ],
        }
        import json
        return json.dumps(selected_profile, ensure_ascii=False)[:settings.DATASET_MAX_SCHEMA_CHARS]
    except Exception as exc:
        logger.warning("Schema retrieval unavailable for dataset %s (%s); using full schema.", dataset.pk, type(exc).__name__)
        return full_schema

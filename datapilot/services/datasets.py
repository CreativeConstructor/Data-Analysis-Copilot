import logging
import uuid
from pathlib import Path
import pandas as pd
from django.conf import settings
from django.db import transaction
from ..models import Dataset

logger = logging.getLogger(__name__)

def read_dataset(path):
    try:
        if str(path).lower().endswith(".csv"):
            frame = pd.read_csv(path, nrows=settings.DATASET_MAX_ROWS + 1)
        else:
            frame = pd.read_excel(path, sheet_name=0, nrows=settings.DATASET_MAX_ROWS + 1, engine="openpyxl")
    except pd.errors.EmptyDataError:
        raise ValueError("The uploaded CSV has no rows or headers.") from None
    except pd.errors.ParserError:
        raise ValueError("The uploaded CSV is malformed.") from None
    except UnicodeDecodeError:
        raise ValueError("The uploaded CSV must use UTF-8 text encoding.") from None
    except Exception as exc:
        if str(path).lower().endswith(".xlsx"):
            raise ValueError("The uploaded XLSX is malformed or has no readable first worksheet.") from None
        raise ValueError("The uploaded dataset could not be parsed.") from None
    if frame.empty:
        raise ValueError("The uploaded dataset is empty.")
    if len(frame) > settings.DATASET_MAX_ROWS:
        raise ValueError(f"Dataset exceeds the {settings.DATASET_MAX_ROWS} row limit.")
    if not len(frame.columns):
        raise ValueError("The dataset has no columns.")
    if len(frame.columns) > settings.DATASET_MAX_COLUMNS:
        raise ValueError(f"Dataset exceeds the {settings.DATASET_MAX_COLUMNS} column limit.")
    if any(not str(column).strip() for column in frame.columns):
        raise ValueError("Every dataset column must have a name.")
    if any(len(str(column)) > 255 for column in frame.columns):
        raise ValueError("Dataset column names must be 255 characters or fewer.")
    frame.columns = [str(column) for column in frame.columns]
    if frame.columns.duplicated().any():
        raise ValueError("Dataset column names must be unique.")
    return frame

def make_profile(frame):
    profile = []
    for column in frame.columns:
        series = frame[column]
        item = {"name": str(column)[:255], "type": str(series.dtype), "missing_count": int(series.isna().sum()),
                "distinct_count": int(series.nunique(dropna=True))}
        if pd.api.types.is_numeric_dtype(series):
            stats = series.describe()
            item["statistics"] = {key: round(float(stats[key]), 4) for key in ("mean", "min", "max", "std") if key in stats and pd.notna(stats[key]) and abs(float(stats[key])) != float("inf")}
        samples = []
        for value in series.dropna().head(5):
            sample = str(value)[:80]
            if sample not in samples:
                samples.append(sample)
        item["samples"] = samples
        profile.append(item)
    summary = {"rows": len(frame), "columns": len(frame.columns), "profile": profile}
    while len(str(summary)) > settings.DATASET_MAX_SCHEMA_CHARS and any(item["samples"] for item in profile):
        for item in profile:
            item["samples"] = item["samples"][:1]
            if len(str(summary)) <= settings.DATASET_MAX_SCHEMA_CHARS:
                break
        if len(str(summary)) > settings.DATASET_MAX_SCHEMA_CHARS and all(len(item["samples"]) <= 1 for item in profile):
            break
    if len(str(summary)) > settings.DATASET_MAX_SCHEMA_CHARS:
        raise ValueError("Dataset schema exceeds the configured profile size limit.")
    return summary

def ingest_upload(owner, uploaded_file):
    name = Path(uploaded_file.name or "").name
    suffix = Path(name).suffix.lower()
    if suffix not in (".csv", ".xlsx"):
        raise ValueError("Only .csv and .xlsx files are supported.")
    if uploaded_file.size == 0:
        raise ValueError("The uploaded file is empty.")
    if uploaded_file.size > settings.DATASET_MAX_UPLOAD_BYTES:
        raise ValueError(f"File exceeds the {settings.DATASET_MAX_UPLOAD_BYTES} byte upload limit.")
    storage_dir = Path(settings.MEDIA_ROOT)
    storage_dir.mkdir(parents=True, exist_ok=True)
    generated_path = storage_dir / f"{uuid.uuid4().hex}{suffix}"
    try:
        with generated_path.open("wb") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        frame = read_dataset(generated_path)
        profile = make_profile(frame)
        with transaction.atomic():
            dataset = Dataset.objects.create(owner=owner, original_filename=name[:255], storage_path=str(generated_path), row_count=len(frame), column_count=len(frame.columns), profile=profile)
        return dataset
    except Exception:
        try:
            generated_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove rejected upload.")
        raise

def delete_dataset(dataset):
    dataset.deleting = True
    dataset.save(update_fields=["deleting"])
    try:
        Path(dataset.storage_path).unlink(missing_ok=True)
    except OSError:
        logger.warning("Dataset file cleanup failed for dataset %s.", dataset.pk)
    dataset.delete()

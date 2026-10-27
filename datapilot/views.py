from pathlib import Path
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Dataset
from .services.datasets import delete_dataset, ingest_upload

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def csrf(request):
    return Response({"csrfToken": get_token(request)})

class DatasetListCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    def get(self, request):
        items = Dataset.objects.filter(owner=request.user, deleting=False).order_by("-created_at")
        return Response([{"id": str(d.id), "original_filename": d.original_filename, "row_count": d.row_count, "column_count": d.column_count, "created_at": d.created_at} for d in items])
    def post(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"error": "Choose a CSV or XLSX file."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            dataset = ingest_upload(request.user, uploaded)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"error": f"Could not process the uploaded dataset ({type(exc).__name__})."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": str(dataset.id), "original_filename": dataset.original_filename,
                         "row_count": dataset.row_count, "column_count": dataset.column_count, "profile": dataset.profile}, status=status.HTTP_201_CREATED)

class DatasetDetailView(APIView):
    def get_object(self, request, pk):
        return get_object_or_404(Dataset, pk=pk, owner=request.user, deleting=False)
    def get(self, request, pk):
        d = self.get_object(request, pk)
        return Response({"id": str(d.id), "original_filename": d.original_filename, "row_count": d.row_count,
                         "column_count": d.column_count, "profile": d.profile, "created_at": d.created_at})
    def delete(self, request, pk):
        with transaction.atomic():
            dataset = get_object_or_404(Dataset.objects.select_for_update(), pk=pk, owner=request.user, deleting=False)
            delete_dataset(dataset)
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    from django.contrib.auth import logout as auth_logout
    auth_logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)

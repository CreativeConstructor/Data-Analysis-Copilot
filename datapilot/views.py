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
from .models import Conversation, Dataset, Turn
from .serializers import AnalyzeSerializer
from .services.datasets import delete_dataset, ingest_upload
from .services.analysis import analyze
from .services.results import format_result
import json

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


class AnalyzeView(APIView):
    def post(self, request):
        serializer = AnalyzeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        dataset = get_object_or_404(Dataset, pk=values["dataset_id"], owner=request.user, deleting=False)
        conversation_id = values.get("conversation_id")
        if conversation_id:
            conversation = get_object_or_404(Conversation, pk=conversation_id, owner=request.user, dataset=dataset)
        else:
            conversation = Conversation.objects.create(owner=request.user, dataset=dataset)
        prior = list(conversation.turns.exclude(status="pending").order_by("-created_at")[:2])
        history = "\n".join(f"Question: {turn.question[:500]} Result: {str(turn.insight)[:300]}" for turn in reversed(prior))
        turn = Turn.objects.create(conversation=conversation, question=values["question"])

        def persist_attempt(attempt):
            turn.attempts = [*turn.attempts, attempt]
            turn.code = attempt.get("code", turn.code)
            turn.save(update_fields=["attempts", "code"])

        columns = [item.get("name", "") for item in dataset.profile.get("profile", [])]
        outcome = analyze(values["question"], json.dumps(dataset.profile), dataset.storage_path,
                          columns=columns, history=history, on_attempt=persist_attempt, dataset=dataset)
        turn.status = outcome["status"]
        turn.code = outcome["code"] or ""
        turn.error = outcome["error"]
        if outcome["status"] == "succeeded":
            turn.table, turn.chart, turn.insight = format_result(outcome["result"])
        turn.save()
        payload = self._turn_payload(turn)
        payload["conversation_id"] = str(conversation.pk)
        return Response(payload, status=200 if turn.status == "succeeded" else 422)

    @staticmethod
    def _turn_payload(turn):
        return {"id": str(turn.pk), "question": turn.question, "status": turn.status,
                "insight": turn.insight, "chart": turn.chart, "table": turn.table,
                "code": turn.code, "attempts": turn.attempts, "error": turn.error,
                "created_at": turn.created_at}


class ConversationDetailView(APIView):
    def get(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk, owner=request.user)
        return Response({"id": str(conversation.pk), "dataset_id": str(conversation.dataset_id),
                         "turns": [AnalyzeView._turn_payload(turn) for turn in conversation.turns.order_by("created_at")]})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    from django.contrib.auth import logout as auth_logout
    auth_logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)

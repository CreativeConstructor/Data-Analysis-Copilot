from rest_framework import serializers


class AnalyzeSerializer(serializers.Serializer):
    dataset_id = serializers.UUIDField()
    question = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)
    conversation_id = serializers.UUIDField(required=False)

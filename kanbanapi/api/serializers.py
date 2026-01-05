"""Serializers for KanbanAPI.

This module contains serializers for converting model instances to/from JSON.
"""

from rest_framework import serializers
from api.models import Article, Tags, OrderProposal


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ["art_no", "art_supplier", "description", "created_at"]


class TagsSerializer(serializers.ModelSerializer):
    art_no = serializers.SlugRelatedField(
        slug_field="art_no", queryset=Article.objects.all()
    )

    class Meta:
        model = Tags
        fields = ["tag_id", "art_no", "status", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def validate_rfid_tag_id(self, value):
        """Validate RFID tag ID format and content.

        Args:
            value: The RFID tag ID to validate

        Returns:
            The validated RFID tag ID

        Raises:
            ValidationError: If the RFID tag ID is invalid
        """
        if not value or not value.strip():
            raise serializers.ValidationError("RFID Tag ID darf nicht leer sein.")

        if len(value) > 24:
            raise serializers.ValidationError(
                "RFID Tag ID darf maximal 24 Zeichen lang sein."
            )

        return value.strip()

    def validate_article_number(self, value):
        """Validate article number format and content.

        Args:
            value: The article number to validate

        Returns:
            The validated article number

        Raises:
            ValidationError: If the article number is invalid
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Artikelnummer darf nicht leer sein.")

        if len(value) > 100:
            raise serializers.ValidationError(
                "Artikelnummer darf maximal 100 Zeichen lang sein."
            )

        return value.strip()


class OrderProposalSerializer(serializers.ModelSerializer):
    """Serializer for OrderProposal with camelCase JSON fields."""

    proposal_id = serializers.IntegerField(source="id", read_only=True)
    fehlmenge = serializers.IntegerField(read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = OrderProposal
        fields = [
            "proposal_id",
            "lieferant",
            "artikelnummer",
            "beschreibung",
            "kanbanGesamt",
            "anwesend",
            "bereitsBestellt",
            "fehlmenge",
            "status",
            "updatedAt",
        ]
        read_only_fields = ["proposal_id", "fehlmenge", "updatedAt"]


class OrderProposalStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating order proposal status."""

    proposal_id = serializers.IntegerField()
    status = serializers.ChoiceField(
        choices=[
            "NEU",
            "GEPRÜFT",
            "FREIGEGEBEN",
            "VERWORFEN",
            "BESTELLT",
            "ABGESCHLOSSEN",
        ]
    )


class OrderProposalSendSerializer(serializers.Serializer):
    """Serializer for batch sending order proposals."""

    supplier = serializers.CharField(max_length=100)
    proposal_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )

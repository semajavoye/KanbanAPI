"""Data models for KanbanAPI.

This module defines the database models following Clean Code principles:
- Single Responsibility Principle
- Meaningful names
- Proper documentation
"""

from django.db import models


class Article(models.Model):
    """Article model storing article numbers and descriptions"""

    art_no = models.CharField(max_length=50, db_index=True)
    art_supplier = models.CharField(
        "Artikel Lieferant",
        help_text="Das ist der Lieferant des Artikels.",
        default="OKB",
        choices=[("OKB", "OKB"), ("SW", "SW"), ("RKB", "RKB")],
        db_index=True,
    )
    kanban_min = models.IntegerField(
        "Kanban Zielmenge",
        default=0,
        help_text="Zielmenge der Kisten, die immer im Lager sein soll",
    )
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Tags(models.Model):
    """RFID tag model linking tag IDs to article numbers"""

    tag_id = models.CharField(max_length=24, db_index=True, primary_key=True)
    art_no = models.ForeignKey(Article, on_delete=models.CASCADE, db_index=True)
    status = models.IntegerField(
        "Status",
        help_text="Der Status der Kanban Box (0=leer, 1=voll).",
        default=0,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OrderProposal(models.Model):
    """Order proposal model for managing Kanban reorder suggestions"""

    STATUS_NEU = "NEU"
    STATUS_GEPRUEFT = "GEPRÜFT"
    STATUS_FREIGEGEBEN = "FREIGEGEBEN"
    STATUS_VERWORFEN = "VERWORFEN"
    STATUS_BESTELLT = "BESTELLT"
    STATUS_ABGESCHLOSSEN = "ABGESCHLOSSEN"

    STATUS_CHOICES = [
        (STATUS_NEU, "Neu"),
        (STATUS_GEPRUEFT, "Geprüft"),
        (STATUS_FREIGEGEBEN, "Freigegeben"),
        (STATUS_VERWORFEN, "Verworfen"),
        (STATUS_BESTELLT, "Bestellt"),
        (STATUS_ABGESCHLOSSEN, "Abgeschlossen"),
    ]

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        db_index=True,
        related_name="order_proposals",
        help_text="Referenz zum Artikel",
    )
    anwesend = models.IntegerField(
        "Anwesend", help_text="Currently present count", default=0
    )
    bereitsBestellt = models.IntegerField(
        "Bereits Bestellt", help_text="Already ordered count", default=0
    )
    status = models.CharField(
        "Status",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEU,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def fehlmenge(self):
        """Calculate shortage: kanban_min - present - already ordered"""
        return max(0, self.article.kanban_min - self.anwesend - self.bereitsBestellt)

    @property
    def lieferant(self):
        """Get supplier from linked article"""
        return self.article.art_supplier

    @property
    def artikelnummer(self):
        """Get article number from linked article"""
        return self.article.art_no

    @property
    def beschreibung(self):
        """Get description from linked article"""
        return self.article.description

    @property
    def kanbanGesamt(self):
        """Get total tag count from linked article"""
        return Tags.objects.filter(art_no=self.article).count()

    @property
    def kanban_min(self):
        """Get kanban_min from linked article"""
        return self.article.kanban_min

    def can_transition_to(self, new_status):
        """Check if status transition is allowed"""
        allowed_transitions = {
            self.STATUS_NEU: [self.STATUS_GEPRUEFT],
            self.STATUS_GEPRUEFT: [self.STATUS_FREIGEGEBEN, self.STATUS_VERWORFEN],
            self.STATUS_FREIGEGEBEN: [self.STATUS_BESTELLT],
            self.STATUS_VERWORFEN: [self.STATUS_GEPRUEFT],
            self.STATUS_BESTELLT: [self.STATUS_ABGESCHLOSSEN],
            self.STATUS_ABGESCHLOSSEN: [],
        }
        return new_status in allowed_transitions.get(self.status, [])

    def update_status(self, new_status):
        """Update status with validation"""
        if not self.can_transition_to(new_status):
            raise ValueError(f"Invalid transition from {self.status} to {new_status}")
        self.status = new_status
        self.save()
        return self

    class Meta:
        ordering = ["-updated_at"]


def delete_order_proposals_if_max_reached(article):
    """Delete order proposals when kanban_min is reached with status=1 tags.

    Args:
        article: Article instance to check

    Returns:
        int: Number of deleted order proposals
    """
    # Count present tags with status=1 (full/present)
    present = Tags.objects.filter(art_no=article, status=1).count()

    # If kanban_min is reached or exceeded, delete open order proposals
    if present >= article.kanban_min:
        deleted_count = OrderProposal.objects.filter(
            article=article,
            status__in=[
                OrderProposal.STATUS_NEU,
                OrderProposal.STATUS_GEPRUEFT,
                OrderProposal.STATUS_FREIGEGEBEN,
            ],
        ).delete()[0]
        return deleted_count

    return 0


def generate_order_proposals_for_article(article, force=False):
    """Helper function to generate order proposals for a specific article.

    Args:
        article: Article instance to generate proposal for
        force: If True, create proposal even if one already exists

    Returns:
        OrderProposal instance if created, None otherwise
    """
    present = Tags.objects.filter(art_no=article, status=1).count()

    # If kanban_min is reached, delete existing proposals
    if present >= article.kanban_min:
        delete_order_proposals_if_max_reached(article)
        return None

    already_ordered = OrderProposal.objects.filter(
        article=article,
        status__in=[
            OrderProposal.STATUS_NEU,
            OrderProposal.STATUS_GEPRUEFT,
            OrderProposal.STATUS_FREIGEGEBEN,
        ],
    ).count()

    shortage = article.kanban_min - present - already_ordered

    if shortage <= 0:
        return None

    # Check if proposal already exists
    existing = OrderProposal.objects.filter(
        article=article,
        status__in=[
            OrderProposal.STATUS_NEU,
            OrderProposal.STATUS_GEPRUEFT,
            OrderProposal.STATUS_FREIGEGEBEN,
        ],
    ).first()

    if existing and not force:
        return None

    # Create new proposal
    return OrderProposal.objects.create(
        article=article,
        anwesend=present,
        bereitsBestellt=0,
        status=OrderProposal.STATUS_NEU,
    )

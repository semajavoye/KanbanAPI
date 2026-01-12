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


class Orders(models.Model):
    """Orders model for orders"""

    order_no = models.CharField(
        max_length=10, unique=True, db_index=True, primary_key=True, editable=False
    )
    art_no = models.CharField(max_length=50, db_index=True)
    status = models.IntegerField(
        "Status",
        help_text="Der Status der Bestellung (0=offen, 1=abgeschlossen).",
        default=0,
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.order_no:
            from api.views import generate_unique_order_no

            self.order_no = generate_unique_order_no()
        if not self.timestamp:
            from django.utils import timezone

            self.timestamp = timezone.now()
        super().save(*args, **kwargs)

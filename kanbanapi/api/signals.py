"""Signal handlers for automatic order proposal generation.

This module contains Django signals that automatically create order proposals
when tag statuses change, ensuring the system always has up-to-date reorder suggestions.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from api.models import (
    Tags,
    generate_order_proposals_for_article,
    delete_order_proposals_if_max_reached,
)


@receiver(post_save, sender=Tags)
def create_order_proposal_on_tag_update(sender, instance, **kwargs):
    """Automatically generate or delete order proposals when a tag is updated.

    This signal fires after a Tags instance is saved, checking if the associated
    article needs reordering based on the current inventory levels. It also deletes
    order proposals if the kanban_min is reached with status=1 tags.

    Args:
        sender: The model class (Tags)
        instance: The actual Tags instance being saved
        **kwargs: Additional signal arguments
    """
    article = instance.art_no

    # First check if we should delete proposals (kanban_min reached)
    delete_order_proposals_if_max_reached(article)

    # Then check if we need to create new proposals (shortage exists)
    generate_order_proposals_for_article(article, force=False)

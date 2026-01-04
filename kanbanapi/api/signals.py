"""Signal handlers for automatic order proposal generation.

This module contains Django signals that automatically create order proposals
when tag statuses change, ensuring the system always has up-to-date reorder suggestions.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from api.models import Tags, generate_order_proposals_for_article


@receiver(post_save, sender=Tags)
def create_order_proposal_on_tag_update(sender, instance, **kwargs):
    """Automatically generate order proposal when a tag is updated.
    
    This signal fires after a Tags instance is saved, checking if the associated
    article needs reordering based on the current inventory levels.
    
    Args:
        sender: The model class (Tags)
        instance: The actual Tags instance being saved
        **kwargs: Additional signal arguments
    """
    article = instance.art_no
    generate_order_proposals_for_article(article, force=False)

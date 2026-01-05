"""Management command to generate order proposals based on Kanban shortage.

This command analyzes all articles and creates order proposals for items
where kanban_min - present - already_ordered > 0.
It also deletes proposals when kanban_min is reached with status=1 tags.
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from api.models import (
    Article,
    Tags,
    OrderProposal,
    delete_order_proposals_if_max_reached,
)


class Command(BaseCommand):
    help = "Generate order proposals for articles with shortage"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating proposals",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Create proposals even if one already exists for this article",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        self.stdout.write("Analyzing articles for order proposals...\n")

        # Get all articles with their tag counts
        articles = Article.objects.all()
        created_count = 0
        skipped_count = 0
        deleted_count = 0

        for article in articles:
            # Count present tags (status=1 means full/present)
            present = Tags.objects.filter(art_no=article, status=1).count()

            # Check if kanban_min is reached and delete proposals if necessary
            if present >= article.kanban_min:
                if dry_run:
                    existing_to_delete = OrderProposal.objects.filter(
                        artikelnummer=article.art_no,
                        status__in=[
                            OrderProposal.STATUS_NEU,
                            OrderProposal.STATUS_GEPRUEFT,
                            OrderProposal.STATUS_FREIGEGEBEN,
                        ],
                    ).count()
                    if existing_to_delete > 0:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  🗑️  Would delete {existing_to_delete} proposal(s) for {article.art_no} "
                                f"(Kanban min {article.kanban_min} reached with {present} present)"
                            )
                        )
                        deleted_count += existing_to_delete
                else:
                    count = delete_order_proposals_if_max_reached(article)
                    if count > 0:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  🗑️  Deleted {count} proposal(s) for {article.art_no} "
                                f"(Kanban min {article.kanban_min} reached with {present} present)"
                            )
                        )
                        deleted_count += count
                continue

            # Count already ordered (sum of bereitsGemeldet for NEU/GEPRÜFT/FREIGEGEBEN proposals)
            already_ordered = (
                OrderProposal.objects.filter(
                    artikelnummer=article.art_no,
                    status__in=[
                        OrderProposal.STATUS_NEU,
                        OrderProposal.STATUS_GEPRUEFT,
                        OrderProposal.STATUS_FREIGEGEBEN,
                    ],
                )
                .aggregate(total=Count("id"))
                .get("total", 0)
            )

            # Calculate shortage
            shortage = article.kanban_min - present - already_ordered

            if shortage > 0:
                # Check if proposal already exists
                existing = OrderProposal.objects.filter(
                    artikelnummer=article.art_no,
                    status__in=[
                        OrderProposal.STATUS_NEU,
                        OrderProposal.STATUS_GEPRUEFT,
                        OrderProposal.STATUS_FREIGEGEBEN,
                    ],
                ).first()

                if existing and not force:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⏭️  {article.art_no}: Proposal already exists (ID {existing.id})"
                        )
                    )
                    skipped_count += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Would create: {article.art_no} "
                            f"(Supplier: {article.art_supplier}, Shortage: {shortage})"
                        )
                    )
                    created_count += 1
                else:
                    # Count total tags for this article
                    total_tags = Tags.objects.filter(art_no=article).count()
                    
                    proposal = OrderProposal.objects.create(
                        lieferant=article.art_supplier,
                        artikelnummer=article.art_no,
                        beschreibung=article.description,
                        kanbanGesamt=total_tags,
                        anwesend=present,
                        bereitsGemeldet=0,  # New proposal, nothing sent yet
                        status=OrderProposal.STATUS_NEU,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Created: {article.art_no} "
                            f"(ID: {proposal.id}, Shortage: {shortage})"
                        )
                    )
                    created_count += 1

        # Summary
        self.stdout.write("\n" + "=" * 50)
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Would create {created_count} proposals")
            )
            if deleted_count > 0:
                self.stdout.write(
                    self.style.WARNING(f"Would delete {deleted_count} proposals")
                )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Created {created_count} new proposals")
            )
            if deleted_count > 0:
                self.stdout.write(
                    self.style.WARNING(f"Deleted {deleted_count} proposals")
                )

        if skipped_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {skipped_count} articles (proposals already exist)"
                )
            )

        self.stdout.write("=" * 50)

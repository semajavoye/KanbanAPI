"""Management command to generate order proposals based on Kanban shortage.

This command analyzes all articles and creates order proposals for items
where kanban_min - present - already_ordered > 0.
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from api.models import Article, Tags, OrderProposal


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

        for article in articles:
            # Count present tags (status=1 means full/present)
            present = Tags.objects.filter(art_no=article, status=1).count()

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
                    proposal = OrderProposal.objects.create(
                        lieferant=article.art_supplier,
                        artikelnummer=article.art_no,
                        beschreibung=article.description,
                        kanbanGesamt=article.kanban_min,
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
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Created {created_count} new proposals")
            )

        if skipped_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {skipped_count} articles (proposals already exist)"
                )
            )

        self.stdout.write("=" * 50)

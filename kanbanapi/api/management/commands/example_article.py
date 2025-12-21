from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import Article
from api.models import Tags


class Command(BaseCommand):
    help = "Append example articles to the database (no overwrite)"

    EXAMPLE_ARTICLES = [
        "K102090",
        "KE109300",
        "VK102",
        "VK103",
        "KE200001",
        "K300500",
    ]

    def handle(self, *args, **options):
        confirm = input("WARNING: This will delete all articles and tags. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING("Operation cancelled."))
            return
        
        self.stdout.write("Starting example article generation...")

        with transaction.atomic():
            # Delete all tags first to avoid foreign key violations
            Tags.objects.all().delete()
            
            # Delete all articles
            Article.objects.all().delete()
            
            # Create new articles
            articles_to_create = [
                Article(
                    art_no=art_no,
                    description=f"Example article {art_no} ÖÄÜß",
                )
                for art_no in self.EXAMPLE_ARTICLES
            ]
            
            Article.objects.bulk_create(articles_to_create)
            
            # Create 20 example tags per article
            articles_dict = {article.art_no: article for article in Article.objects.all()}
            tags_to_create = [
                Tags(
                    tag_id=format(hash((art_no, i)) & 0xffffff, '024x'),
                    art_no_id=articles_dict[art_no].id,
                    status=i % 2,  # Alternate between 0 and 1
                )
                for art_no in self.EXAMPLE_ARTICLES
                for i in range(20)
            ]
            
            Tags.objects.bulk_create(tags_to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(articles_to_create)} example articles and {len(tags_to_create)} example tags successfully."
            )
        )

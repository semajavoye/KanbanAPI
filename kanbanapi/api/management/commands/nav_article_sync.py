import os
import pyodbc
from django.db import transaction
from django_tqdm import BaseCommand
from api.models import Article


class Command(BaseCommand):
    """
    Django Management Command zur Synchronisation von Artikeln mit Navision.

    Synchronisiert Artikel-Daten von Microsoft Dynamics NAV
    in die Django-Datenbank (Article Model).

    Verwendung:
        python manage.py nav_article_sync

    Attributes:
        help (str): Hilfetext für das Command
    """

    help = "Synchronize Articles with Navision"

    def _get_nav_connection(self):
        """Build a pyodbc connection from environment variables in settings.

        Required env vars (loaded in settings.py):
        - NAV_HOST
        - NAV64BIT_USER
        - NAV64BIT_PASSWORD
        Optional:
        - NAV_DATABASE (default: NAV501)
        - NAV_ODBC_DRIVER (default: ODBC Driver 17 for SQL Server)
        """
        host = os.environ.get("NAV_HOST")
        user = os.environ.get("NAV64BIT_USER")
        password = os.environ.get("NAV64BIT_PASSWORD")
        database = os.environ.get("NAV_DATABASE", "NAV501")
        driver = os.environ.get("NAV_ODBC_DRIVER", "ODBC Driver 17 for SQL Server")

        if not host or not user or not password:
            raise RuntimeError(
                "NAV connection env vars missing: NAV_HOST, NAV64BIT_USER, NAV64BIT_PASSWORD"
            )

        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={host};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )
        return pyodbc.connect(conn_str)

    def handle(self, *args, **kwargs):
        """
        Führt die Artikel-Synchronisation aus.

        Liest alle Artikel aus dem NAV-System und
        aktualisiert/erstellt entsprechende Einträge in der Django-DB.
        Zeigt Fortschrittsbalken mit django-tqdm.

        Args:
            *args: Positions-Argumente (nicht verwendet)
            **kwargs: Keyword-Argumente (nicht verwendet)
        """
        conn = self._get_nav_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT [No_], [Description]
                FROM [dbo].[OTEC$Item]
                """
            )
            rows = cur.fetchall()

            self.stdout.write(f"Fetched {len(rows)} articles from NAV. Starting bulk sync...")

            with transaction.atomic():
                articles_to_update = []
                articles_to_create = []

                existing_articles = {art.art_no: art for art in Article.objects.all()}

                t = self.tqdm(total=len(rows))
                for no, desc in rows:
                    desc = desc or ""

                    if no in existing_articles:
                        article = existing_articles[no]
                        article.description = desc
                        articles_to_update.append(article)
                    else:
                        articles_to_create.append(
                            Article(
                                art_no=no,
                                description=desc,
                            )
                        )
                    t.update(1)

                if articles_to_create:
                    Article.objects.bulk_create(articles_to_create, batch_size=1000)
                    self.stdout.write(self.style.SUCCESS(f"Created {len(articles_to_create)} new articles"))

                if articles_to_update:
                    Article.objects.bulk_update(
                        articles_to_update, ["description"], batch_size=1000
                    )
                    self.stdout.write(self.style.SUCCESS(f"Updated {len(articles_to_update)} existing articles"))

            self.stdout.write(self.style.SUCCESS(f"Sync complete! Total: {len(rows)} articles"))
        finally:
            conn.close()

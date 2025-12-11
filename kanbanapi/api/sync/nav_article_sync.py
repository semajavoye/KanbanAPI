import os
import pyodbc
from django.db import transaction
from api.models import Article


def _get_nav_connection():
    """Build a pyodbc connection from environment variables in settings.

    Required env vars (loaded in settings.py):
    - NAV_HOST
    - NAV64BIT_USER
    - NAV64BIT_PASSWORD
    Optional:
    - NAV_DATABASE (default: NAV501)
    - NAV_ODBC_DRIVER (default: ODBC Driver 18 for SQL Server)
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

    # Correct ODBC connection string formatting
    # Example: DRIVER={ODBC Driver 18 for SQL Server};SERVER=host;DATABASE=db;UID=user;PWD=pass;TrustServerCertificate=yes;
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={host};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)


def run_sync():
    """Synchronize NAV items into Article table using configured NAV connection."""
    conn = _get_nav_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT [No_], [Description]
            FROM [dbo].[OTEC$Item]
            """
        )
        # Fetch ALL rows at once
        rows = cur.fetchall()

        print(f"Fetched {len(rows)} articles from NAV. Starting bulk sync...")

        with transaction.atomic():
            # Prepare bulk lists
            articles_to_update = []
            articles_to_create = []

            # Get existing articles with their descriptions
            existing_articles = {art.art_no: art for art in Article.objects.all()}

            for no, desc in rows:
                desc = desc or ""

                if no in existing_articles:
                    # Update existing article's description
                    article = existing_articles[no]
                    article.description = desc
                    articles_to_update.append(article)
                else:
                    # Create new article
                    articles_to_create.append(
                        Article(
                            art_no=no,
                            description=desc,
                        )
                    )

            # Bulk create new articles
            if articles_to_create:
                Article.objects.bulk_create(articles_to_create, batch_size=1000)
                print(f"Created {len(articles_to_create)} new articles")

            # Bulk update existing articles
            if articles_to_update:
                Article.objects.bulk_update(
                    articles_to_update, ["description"], batch_size=1000
                )
                print(f"Updated {len(articles_to_update)} existing articles")

        print(f"Sync complete! Total: {len(rows)} articles")
    finally:
        conn.close()

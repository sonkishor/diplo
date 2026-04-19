import time

from django.core.management.base import BaseCommand

from ingestion.sources.gdelt import GDELTIngester


class Command(BaseCommand):
    help = "Pull a specific historical GDELT file by date"

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, required=True)
        parser.add_argument("--time", type=str, default="120000")

    def handle(self, *args, **options):
        date = options["date"]
        time_str = options["time"]

        export_url = (
            f"http://data.gdeltproject.org/gdeltv2/{date}{time_str}.export.CSV.zip"
        )
        mentions_url = (
            f"http://data.gdeltproject.org/gdeltv2/{date}{time_str}.mentions.CSV.zip"
        )

        self.stdout.write(f"Fetching events: {export_url}")
        ingester = GDELTIngester()

        df = ingester._download_and_parse(export_url)
        self.stdout.write(f"Total rows: {len(df)}")

        events = ingester._filter_india_events(df)
        self.stdout.write(f"India events found: {len(events)}")

        # Fetch headlines from mentions file
        self.stdout.write("Fetching mentions for headlines...")
        headlines = ingester._fetch_mentions_headlines(mentions_url)

        time.sleep(2)  # TODO: throttle remove
        self.stdout.write(f"Got {len(headlines)} headlines from mentions")

        saved = ingester._save_events_with_headlines(events, headlines)
        self.stdout.write(self.style.SUCCESS(f"Saved: {saved} new events"))

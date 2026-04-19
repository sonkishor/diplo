from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Pull latest GDELT export and save India-related events"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Parse but do not save to DB")

    def handle(self, *args, **options):
        from ingestion.sources.gdelt import GDELTIngester

        self.stdout.write("Fetching latest GDELT file...")
        ingester = GDELTIngester()

        if options["dry_run"]:
            url = ingester._get_latest_csv_url()
            self.stdout.write(f"URL: {url}")
            df = ingester._download_and_parse(url)
            self.stdout.write(f"Total rows: {len(df)}")
            events = ingester._filter_india_events(df)
            self.stdout.write(self.style.SUCCESS(
                f"India events found: {len(events)}"
            ))
            for ev in events[:5]:
                self.stdout.write(
                    f"  [{ev.sentiment:8}] [{ev.event_type:12}] "
                    f"India <-> {ev.country_iso} | "
                    f"Goldstein: {ev.goldstein:+.1f}"
                )
        else:
            count = ingester.run()
            self.stdout.write(self.style.SUCCESS(
                f"Done — {count} new events saved"
            ))

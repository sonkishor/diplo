import io
import logging
import zipfile
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Correct GDELT 2.0 column indices
# Full schema: http://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf
COL_EVENT_ID = 0
COL_DATE = 1
COL_ACTOR1_NAME = 6
COL_ACTOR1_COUNTRY = 7
COL_ACTOR2_NAME = 16
COL_ACTOR2_COUNTRY = 17
COL_EVENT_CODE = 26
COL_GOLDSTEIN = 30
COL_NUM_ARTICLES = 33
COL_ACTION_LAT = 56
COL_ACTION_LONG = 57
COL_SOURCE_URL = 60

INDIA_CODE = "IND"

INVALID_ACTOR_CODES = {
    "GOV",
    "MIL",
    "REB",
    "OPP",
    "PTY",
    "CVL",
    "MED",
    "EDU",
    "BUS",
    "CRM",
    "LEG",
    "JUD",
    "SPY",
    "IGO",
    "NGO",
    "INT",
    "JAN",
    "SET",
    "REL",
    "UAF",
    "MOD",
}

CAMEO_CATEGORIES = {
    "01": "statement",
    "02": "appeal",
    "03": "agreement",
    "04": "consultation",
    "05": "diplomatic",
    "06": "diplomatic",
    "07": "agreement",
    "08": "agreement",
    "09": "military",
    "10": "diplomatic",
    "11": "diplomatic",
    "12": "diplomatic",
    "13": "military",
    "14": "protest",
    "15": "incident",
    "16": "incident",
    "17": "incident",
    "18": "incident",
    "19": "military",
    "20": "military",
}


@dataclass
class GDELTEvent:
    event_id: str
    event_date: datetime
    actor1_name: str
    actor1_country: str
    actor2_name: str
    actor2_country: str
    event_code: str
    event_type: str
    goldstein: float
    num_articles: int
    country_iso: str
    latitude: float | None
    longitude: float | None
    source_url: str
    sentiment: str


class GDELTIngester:
    MASTER_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"

    def run(self) -> int:
        logger.info("GDELT ingestion started")
        try:
            csv_url = self._get_latest_csv_url()
            logger.info(f"Fetching: {csv_url}")
            df = self._download_and_parse(csv_url)
            logger.info(f"Downloaded {len(df)} raw rows")
            events = self._filter_india_events(df)
            logger.info(f"Found {len(events)} India events")
            saved = self._save_events(events)
            logger.info(f"Saved {saved} new events")
            return saved
        except Exception as e:
            logger.error(f"GDELT ingestion failed: {e}", exc_info=True)
            raise

    def run_historical(self, url: str) -> int:
        df = self._download_and_parse(url)
        events = self._filter_india_events(df)
        return self._save_events(events)

    def _get_latest_csv_url(self) -> str:
        response = requests.get(self.MASTER_URL, timeout=10)
        response.raise_for_status()
        first_line = response.text.strip().splitlines()[0]
        return first_line.split(" ")[2]

    def _download_and_parse(self, url: str) -> pd.DataFrame:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            with zf.open(zf.namelist()[0]) as f:
                df = pd.read_csv(
                    f, sep="\t", header=None, dtype=str, on_bad_lines="skip"
                )
        return df

    def _filter_india_events(self, df: pd.DataFrame) -> list:
        if df.shape[1] <= COL_SOURCE_URL:
            logger.warning(f"File has only {df.shape[1]} columns, expected 61+")
            return []
        a1_india = df[COL_ACTOR1_COUNTRY] == INDIA_CODE
        a2_india = df[COL_ACTOR2_COUNTRY] == INDIA_CODE
        both = a1_india & a2_india
        rows = df[(a1_india | a2_india) & ~both]
        return [e for _, r in rows.iterrows() if (e := self._parse_row(r))]

    def _parse_row(self, row):
        try:
            a1 = self._safe(row, COL_ACTOR1_COUNTRY)
            a2 = self._safe(row, COL_ACTOR2_COUNTRY)
            other = a2 if a1 == INDIA_CODE else a1
            if not other or other == INDIA_CODE or other in INVALID_ACTOR_CODES:
                return None
            code = self._safe(row, COL_EVENT_CODE) or ""
            goldstein = self._safe_float(row, COL_GOLDSTEIN)
            source = self._safe(row, COL_SOURCE_URL) or ""
            if not source.startswith("http"):
                return None
            return GDELTEvent(
                event_id=self._safe(row, COL_EVENT_ID) or "",
                event_date=self._parse_date(self._safe(row, COL_DATE)),
                actor1_name=self._safe(row, COL_ACTOR1_NAME) or "",
                actor1_country=a1 or "",
                actor2_name=self._safe(row, COL_ACTOR2_NAME) or "",
                actor2_country=a2 or "",
                event_code=code,
                event_type=self._map_event_type(code),
                goldstein=goldstein or 0.0,
                num_articles=int(self._safe(row, COL_NUM_ARTICLES) or 1),
                country_iso=other,
                latitude=self._safe_float(row, COL_ACTION_LAT),
                longitude=self._safe_float(row, COL_ACTION_LONG),
                source_url=source,
                sentiment=self._map_sentiment(goldstein),
            )
        except Exception:
            return None

    def _save_events(self, events: list) -> int:
        from ingestion.models import DiplomaticEvent

        saved = 0
        for ev in events:
            if DiplomaticEvent.objects.filter(source_url=ev.source_url).exists():
                continue
            _, created = DiplomaticEvent.objects.get_or_create(
                gdelt_event_id=ev.event_id,
                defaults={
                    "country_iso": ev.country_iso,
                    "event_date": ev.event_date,
                    "headline": f"{ev.actor1_name or 'India'} — {ev.event_type} — {ev.actor2_name or ev.country_iso}",
                    "event_type": ev.event_type,
                    "sentiment": ev.sentiment,
                    "goldstein": ev.goldstein,
                    "num_articles": ev.num_articles,
                    "latitude": ev.latitude,
                    "longitude": ev.longitude,
                    "source_url": ev.source_url,
                    "source": "GDELT",
                },
            )
            if created:
                saved += 1
        return saved

    def _safe(self, row, col):
        try:
            val = row.iloc[col]
            return str(val).strip() if pd.notna(val) else None
        except (IndexError, KeyError):
            return None

    def _safe_float(self, row, col):
        try:
            val = row.iloc[col]
            return float(val) if pd.notna(val) else None
        except (IndexError, KeyError, ValueError):
            return None

    def _parse_date(self, date_str):
        from django.utils import timezone

        if not date_str:
            return timezone.now()
        try:
            naive = datetime.strptime(date_str[:8], "%Y%m%d")
            return timezone.make_aware(naive)
        except ValueError:
            return timezone.now()

    def _map_sentiment(self, goldstein):
        if goldstein is None:
            return "neutral"
        if goldstein > 1.0:
            return "positive"
        if goldstein < -1.0:
            return "negative"
        return "neutral"

    def _map_event_type(self, code):
        return CAMEO_CATEGORIES.get(code[:2] if len(code) >= 2 else "", "statement")

    def _fetch_mentions_headlines(self, mentions_url: str) -> dict:
        """
        Originally was designed for fetching the headlines, but now repurposed for the timestamp
        Returns dict of {event_id: {'time': datetime, }}
        Col 0 = EventID
        Col 2 = MentionTimeDate (YYYYMMDDHHMMSS) ← precise timestamp
        """
        try:
            response = requests.get(mentions_url, timeout=30)
            response.raise_for_status()

            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                with zf.open(zf.namelist()[0]) as f:
                    df = pd.read_csv(
                        f, sep="\t", header=None, dtype=str, on_bad_lines="skip"
                    )

            result = {}
            for _, row in df.iterrows():
                try:
                    event_id = str(row.iloc[0]).strip()
                    time_str = str(row.iloc[2]).strip()  # MentionTimeDate

                    if event_id in result:
                        continue

                    # Parse YYYYMMDDHHMMSS
                    from django.utils import timezone

                    naive = datetime.strptime(time_str[:14], "%Y%m%d%H%M%S")
                    aware = timezone.make_aware(naive)

                    result[event_id] = aware

                except Exception:
                    continue

            return result

        except Exception as e:
            logger.warning(f"Could not fetch mentions: {e}")
            return {}

    def _save_events_with_headlines(self, events: list, mentions: dict) -> int:
        from ingestion.models import DiplomaticEvent

        saved = 0
        for ev in events:
            if DiplomaticEvent.objects.filter(source_url=ev.source_url).exists():
                continue

            # Use precise timestamp from mentions if available
            event_time = mentions.get(ev.event_id, ev.event_date)

            _, created = DiplomaticEvent.objects.get_or_create(
                gdelt_event_id=ev.event_id,
                defaults={
                    "country_iso": ev.country_iso,
                    "event_date": event_time,
                    "headline": f"India — {ev.event_type.title()} — {ev.country_iso}",
                    "event_type": ev.event_type,
                    "sentiment": ev.sentiment,
                    "goldstein": ev.goldstein,
                    "num_articles": ev.num_articles,
                    "latitude": ev.latitude,
                    "longitude": ev.longitude,
                    "source_url": ev.source_url,
                    "source": "GDELT",
                },
            )
            if created:
                saved += 1
        return saved

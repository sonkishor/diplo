from django.db import models


class DiplomaticEvent(models.Model):
    objects: models.Manager["DiplomaticEvent"]
    SENTIMENT_CHOICES = [
        ("positive", "Positive"),
        ("negative", "Negative"),
        ("neutral", "Neutral"),
    ]
    EVENT_TYPE_CHOICES = [
        ("statement", "Statement"),
        ("appeal", "Appeal"),
        ("agreement", "Agreement"),
        ("consultation", "Consultation"),
        ("diplomatic", "Diplomatic"),
        ("military", "Military"),
        ("incident", "Incident"),
        ("protest", "Protest"),
    ]

    gdelt_event_id = models.CharField(max_length=50, unique=True, db_index=True)
    country_iso = models.CharField(max_length=3, db_index=True)
    event_date = models.DateTimeField(db_index=True)
    headline = models.CharField(max_length=500)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES)
    goldstein = models.FloatField(default=0.0)
    num_articles = models.IntegerField(default=1)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    source_url = models.URLField(max_length=800, unique=True)
    source = models.CharField(max_length=50, default="GDELT")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-event_date"]
        indexes = [
            models.Index(fields=["country_iso", "event_date"]),
            models.Index(fields=["sentiment", "event_date"]),
        ]

    def __str__(self):
        return f"{self.country_iso} | {self.sentiment} | {self.event_date:%Y-%m-%d}"

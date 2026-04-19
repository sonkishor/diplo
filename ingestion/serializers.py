from rest_framework import serializers
from .models import DiplomaticEvent


class DiplomaticEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiplomaticEvent
        fields = [
            "id",
            "country_iso",
            "event_date",
            "headline",
            "event_type",
            "sentiment",
            "goldstein",
            "num_articles",
            "latitude",
            "longitude",
            "source_url",
            "source",
        ]

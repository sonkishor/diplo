from datetime import timedelta

from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DiplomaticEvent
from .serializers import DiplomaticEventSerializer


class EventListView(generics.ListAPIView):
    serializer_class = DiplomaticEventSerializer

    def get_queryset(self):
        qs = DiplomaticEvent.objects.all()

        # Filter by country
        country = self.request.query_params.get("country")
        if country:
            qs = qs.filter(country_iso__iexact=country)

        # Filter by last N days
        days = self.request.query_params.get("days")
        if days:
            since = timezone.now() - timedelta(days=int(days))
            qs = qs.filter(event_date__gte=since)

        # Filter by sentiment
        sentiment = self.request.query_params.get("sentiment")
        if sentiment:
            qs = qs.filter(sentiment=sentiment)

        return qs.order_by("-event_date")


class CountrySummaryView(APIView):
    def get(self, request):
        from django.db.models import Avg, Count, Q

        days = request.query_params.get("days", 30)
        since = timezone.now() - timedelta(days=int(days))

        data = (
            DiplomaticEvent.objects.filter(event_date__gte=since)
            .values("country_iso")
            .annotate(
                event_count=Count("id"),
                avg_goldstein=Avg("goldstein"),
                positive_count=Count("id", filter=Q(sentiment="positive")),
                negative_count=Count("id", filter=Q(sentiment="negative")),
                neutral_count=Count("id", filter=Q(sentiment="neutral")),
                incident_count=Count(
                    "id", filter=Q(event_type__in=["incident", "military"])
                ),
            )
            .order_by("-event_count")
        )

        result = []
        for row in data:
            total = row["event_count"]
            positive = row["positive_count"]
            negative = row["negative_count"]
            incidents = row["incident_count"]
            avg = row["avg_goldstein"] or 0

            # Weighted sentiment score
            # Incidents drag the score down hard
            score = (
                (positive / total * 10)
                - (negative / total * 10)
                - (incidents / total * 5)
                + (avg * 0.5)
            )

            if score > 3:
                sentiment = "positive"
            elif score < -1:
                sentiment = "negative"
            else:
                sentiment = "neutral"

            result.append(
                {
                    "country_iso": row["country_iso"],
                    "event_count": total,
                    "avg_goldstein": round(avg, 2),
                    "positive_count": positive,
                    "negative_count": negative,
                    "incident_count": incidents,
                    "sentiment": sentiment,
                }
            )

        return Response(result)

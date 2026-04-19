from django.urls import path
from .views import EventListView, CountrySummaryView

urlpatterns = [
    path("events/",   EventListView.as_view(),    name="events"),
    path("summary/",  CountrySummaryView.as_view(), name="summary"),
]

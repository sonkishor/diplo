import { Component, OnInit } from "@angular/core";
import * as L from "leaflet";
import { HttpClient } from "@angular/common/http";

@Component({
  selector: "app-map",
  templateUrl: "./map.component.html",
  styleUrls: ["./map.component.scss"],
})
export class MapComponent implements OnInit {
  private map!: L.Map;
  private markers: L.CircleMarker[] = [];

  allEvents: any[] = [];
  filteredEvents: any[] = [];
  selectedEvent: any = null;
  searchQuery = "";
  loading = true;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.initMap();
    this.loadEvents();
  }

  private initMap(): void {
    this.map = L.map("map", {
      center: [20, 78],
      zoom: 3,
      minZoom: 2,
      maxZoom: 8,
      zoomControl: false,
      maxBounds: [
        [-90, -180],
        [90, 180],
      ], // hard world limits
      maxBoundsViscosity: 1.0, // 1.0 = hard stop, 0.5 = elastic
    });

    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      {
        attribution: "&copy; OpenStreetMap &copy; CARTO",
        subdomains: "abcd",
      },
    ).addTo(this.map);

    L.control.zoom({ position: "bottomright" }).addTo(this.map);
  }

  private loadEvents(): void {
    const baseUrl = window.location.origin;

    this.http.get<any>(`${baseUrl}/api/events/?days=30`).subscribe((data) => {
      this.allEvents = data.results;
      this.filteredEvents = data.results;
      this.loading = false;
      this.plotMarkers(data.results);
    });
  }

  private plotMarkers(events: any[]): void {
    // Clear existing markers
    this.markers.forEach((m) => m.remove());
    this.markers = [];

    events.forEach((ev) => {
      if (!ev.latitude || !ev.longitude) return;

      const color = this.getSentimentColor(ev.sentiment);

      const marker = L.circleMarker([ev.latitude, ev.longitude], {
        radius: 6,
        fillColor: color,
        fillOpacity: 0.85,
        color: "#ffffff",
        weight: 1,
      }).addTo(this.map);

      marker.on("click", () => this.selectEvent(ev));
      this.markers.push(marker);
    });
  }

  selectEvent(ev: any): void {
    this.selectedEvent = ev;
    if (ev.latitude && ev.longitude) {
      this.map.panTo([ev.latitude, ev.longitude], { animate: true });
    }
    // Scroll feed to this event
    setTimeout(() => {
      const el = document.getElementById(`event-${ev.id}`);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 100);
  }

  onSearch(): void {
    const q = this.searchQuery.toLowerCase().trim();
    if (!q) {
      this.filteredEvents = this.allEvents;
    } else {
      this.filteredEvents = this.allEvents.filter(
        (ev) =>
          ev.country_iso.toLowerCase().includes(q) ||
          ev.headline.toLowerCase().includes(q) ||
          ev.event_type.toLowerCase().includes(q),
      );
    }
    this.plotMarkers(this.filteredEvents);
  }

  clearSearch(): void {
    this.searchQuery = "";
    this.filteredEvents = this.allEvents;
    this.plotMarkers(this.allEvents);
  }

  getSentimentColor(sentiment: string): string {
    if (sentiment === "positive") return "#22c55e";
    if (sentiment === "negative") return "#ef4444";
    return "#94a3b8";
  }

  getSentimentLabel(sentiment: string): string {
    if (sentiment === "positive") return "POS";
    if (sentiment === "negative") return "NEG";
    return "NEU";
  }

  formatDate(dateStr: string): string {
    const now = new Date();
    const d = new Date(dateStr);
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 30) return `${diffDays}d ago`;
    return `${Math.floor(diffDays / 30)}mo ago`;
  }
}

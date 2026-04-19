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
  private geojsonLayer!: L.GeoJSON;
  private activeCountries: Set<string> = new Set();
  selectedCountry: string | null = null;
  public events: any[] = [];
  public loadingEvents = false;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.initMap();
    this.loadActiveCountries();
  }

  private initMap(): void {
    this.map = L.map("map", {
      center: [20, 0],
      zoom: 2,
      minZoom: 2,
      maxZoom: 6,
      zoomControl: true,
    });

    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      {
        attribution: "&copy; OpenStreetMap &copy; CARTO",
        subdomains: "abcd",
      },
    ).addTo(this.map);

    // Labels on top
    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png",
      {
        attribution: "",
        subdomains: "abcd",
      },
    ).addTo(this.map);
  }

  private loadActiveCountries(): void {
    this.http
      .get<any[]>("http://localhost:8000/api/summary/")
      .subscribe((data) => {
        data.forEach((d) => this.activeCountries.add(d.country_iso));
        this.loadGeoJSON();
      });
  }

  private loadGeoJSON(): void {
    this.http.get("/assets/countries.geojson").subscribe((geojson: any) => {
      this.geojsonLayer = L.geoJSON(geojson, {
        style: (feature) => this.styleFeature(feature),
        onEachFeature: (feature, layer) => {
          const iso = feature.properties.ISO_A3;
          if (this.activeCountries.has(iso)) {
            layer.on("click", () => this.onCountryClick(iso));
            layer.on("mouseover", (e) => {
              (e.target as L.Path).setStyle({ fillOpacity: 0.9 });
            });
            layer.on("mouseout", (e) => {
              this.geojsonLayer.resetStyle(e.target);
            });
          }
        },
      }).addTo(this.map);
    });
  }

  private styleFeature(feature: any): L.PathOptions {
    const iso = feature?.properties?.ISO_A3;
    const isActive = this.activeCountries.has(iso);

    return {
      fillColor: isActive ? "#f97316" : "#1e293b",
      fillOpacity: isActive ? 0.7 : 0.3,
      color: "#334155",
      weight: 0.5,
    };
  }

  onCountryClick(iso: string): void {
    this.selectedCountry = iso;
    this.loadingEvents = true;
    this.events = [];

    this.http
      .get<any>(`http://localhost:8000/api/events/?country=${iso}&days=30`)
      .subscribe((data) => {
        this.events = data.results;
        this.loadingEvents = false;
      });
  }

  getSentimentClass(sentiment: string): string {
    if (sentiment === "positive") return "positive";
    if (sentiment === "negative") return "negative";
    return "neutral";
  }
}

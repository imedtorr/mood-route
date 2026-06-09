import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Polyline, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import type { ItineraryStop } from "@/lib/types";
import "leaflet/dist/leaflet.css";

const iconCache = new Map<number, L.DivIcon>();

function numberedIcon(n: number): L.DivIcon {
  if (!iconCache.has(n)) {
    iconCache.set(
      n,
      L.divIcon({
        className: "moodroute-marker",
        html: `<span style="display:flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:9999px;background:#c45c26;color:#fff;font-weight:600;font-size:12px;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.25)">${n}</span>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      }),
    );
  }
  return iconCache.get(n)!;
}

function FitBounds({ stops }: { stops: ItineraryStop[] }) {
  const map = useMap();
  useEffect(() => {
    const coords = stops
      .filter((s) => s.lat != null && s.lng != null)
      .map((s) => [s.lat!, s.lng!] as [number, number]);
    if (coords.length >= 2) {
      map.fitBounds(L.latLngBounds(coords), { padding: [32, 32] });
    } else if (coords.length === 1) {
      map.setView(coords[0], 14);
    } else {
      map.setView([35.6762, 139.6503], 12);
    }
  }, [map, stops]);
  return null;
}

export function MapPanel({ stops }: { stops: ItineraryStop[] }) {
  const coords = stops
    .filter((s) => s.lat != null && s.lng != null)
    .map((s) => [s.lat!, s.lng!] as [number, number]);
  const missingCount = stops.filter((s) => s.lat == null || s.lng == null).length;

  return (
    <div>
      {missingCount > 0 && (
        <div className="border-b border-border bg-warning/10 px-4 py-2 text-xs text-warning">
          {missingCount} stops without coordinates not shown on map
        </div>
      )}
      <MapContainer
        center={[35.6762, 139.6503]}
        zoom={12}
        className="h-[420px] w-full"
        scrollWheelZoom={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds stops={stops} />
        {stops.map((s) =>
          s.lat != null && s.lng != null ? (
            <Marker key={s.n} position={[s.lat, s.lng]} icon={numberedIcon(s.n)}>
              <Popup>
                <div className="space-y-1 text-sm">
                  <div className="font-medium">{s.title}</div>
                  {(s.address || s.district) && (
                    <div className="text-muted-foreground">{s.address || s.district}</div>
                  )}
                </div>
              </Popup>
            </Marker>
          ) : null,
        )}
        {coords.length >= 2 && (
          <Polyline
            positions={coords}
            pathOptions={{ color: "#c45c26", weight: 3, dashArray: "6 8" }}
          />
        )}
      </MapContainer>
    </div>
  );
}

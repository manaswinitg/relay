import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

export default function MapView({
  shelters = [],
  reports = [],
  selectedCoords = null,
  onMapClick = null,
  center = [37.7749, -122.4194],
  zoom = 12
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current).setView(center, zoom);

      // OpenStreetMap standard tile layer
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18
      }).addTo(map);

      markersLayerRef.current = L.layerGroup().addTo(map);

      // Map click handler
      if (onMapClick) {
        map.on('click', (e) => {
          onMapClick({
            latitude: Number(e.latlng.lat.toFixed(5)),
            longitude: Number(e.latlng.lng.toFixed(5))
          });
        });
      }

      mapInstanceRef.current = map;
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update Markers
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return;

    markersLayerRef.current.clearLayers();

    // 1. Shelter Markers
    shelters.forEach((s) => {
      if (!s.latitude || !s.longitude) return;

      const occupancyRate = s.total_capacity > 0 ? (s.current_occupancy / s.total_capacity) * 100 : 0;
      let badgeColor = '#10b981'; // green
      if (s.status === 'FULL' || occupancyRate >= 100) badgeColor = '#f59e0b'; // amber
      if (s.status === 'EVACUATING' || s.status === 'CLOSED') badgeColor = '#ef4444'; // red

      const customIcon = L.divIcon({
        className: 'custom-shelter-pin',
        html: `
          <div style="background-color: ${badgeColor}; width: 28px; height: 28px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 11px;">
            S
          </div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
        popupAnchor: [0, -14]
      });

      const marker = L.marker([s.latitude, s.longitude], { icon: customIcon });
      marker.bindPopup(`
        <div style="font-family: sans-serif; font-size: 13px; line-height: 1.4;">
          <strong style="font-size: 14px; color: #0f172a;">${s.name}</strong><br/>
          <span style="color: #64748b;">${s.address}</span><br/>
          <div style="margin-top: 6px; padding: 4px 8px; background: #f1f5f9; border-radius: 4px;">
            <strong>Status:</strong> <span style="color: ${badgeColor}; font-weight: 600;">${s.status}</span><br/>
            <strong>Occupancy:</strong> ${s.current_occupancy} / ${s.total_capacity} (${Math.round(occupancyRate)}%)<br/>
            ${s.contact_phone ? `<strong>Phone:</strong> ${s.contact_phone}` : ''}
          </div>
        </div>
      `);
      markersLayerRef.current.addLayer(marker);
    });

    // 2. Emergency Report Markers
    reports.forEach((r) => {
      if (!r.latitude || !r.longitude) return;

      let reportColor = '#f97316'; // orange (Medium)
      if (r.urgency === 'CRITICAL') reportColor = '#dc2626'; // dark red
      if (r.urgency === 'HIGH') reportColor = '#ea580c'; // red-orange
      if (r.urgency === 'LOW') reportColor = '#eab308'; // yellow

      const reportIcon = L.divIcon({
        className: 'custom-report-pin',
        html: `
          <div style="background-color: ${reportColor}; width: 22px; height: 22px; border-radius: 4px; border: 2px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 10px;">
            !
          </div>
        `,
        iconSize: [22, 22],
        iconAnchor: [11, 11],
        popupAnchor: [0, -11]
      });

      const marker = L.marker([r.latitude, r.longitude], { icon: reportIcon });
      marker.bindPopup(`
        <div style="font-family: sans-serif; font-size: 12px; line-height: 1.3;">
          <div style="display: inline-block; padding: 2px 6px; border-radius: 3px; font-weight: bold; background: ${reportColor}; color: white; margin-bottom: 4px;">
            ${r.urgency} • ${r.category}
          </div><br/>
          <strong>Report:</strong> ${r.raw_text}<br/>
          ${r.reporter_name ? `<span style="color: #64748b;">Reported by: ${r.reporter_name}</span>` : ''}
        </div>
      `);
      markersLayerRef.current.addLayer(marker);
    });

    // 3. User Selected Coordinates Pin
    if (selectedCoords?.latitude && selectedCoords?.longitude) {
      const selectedIcon = L.divIcon({
        className: 'custom-selected-pin',
        html: `
          <div style="background-color: #3b82f6; width: 18px; height: 18px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 10px #3b82f6;"></div>
        `,
        iconSize: [18, 18],
        iconAnchor: [9, 9]
      });
      const selectedMarker = L.marker([selectedCoords.latitude, selectedCoords.longitude], { icon: selectedIcon });
      selectedMarker.bindPopup('<strong>Selected Pin Location</strong>');
      markersLayerRef.current.addLayer(selectedMarker);
    }
  }, [shelters, reports, selectedCoords]);

  return (
    <div className="w-full h-full relative rounded-xl overflow-hidden shadow-inner border border-slate-200">
      <div ref={mapContainerRef} className="w-full h-full min-h-[420px]" />
    </div>
  );
}

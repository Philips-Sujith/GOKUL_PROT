import React, { useEffect, useRef, useState, useMemo } from 'react';
import L from 'leaflet';
import { Layers, Activity, Maximize2, Info, Compass, ShieldCheck } from 'lucide-react';
import { DistrictSummary } from '../types';

interface GisMapProps {
  districts: DistrictSummary[];
  selectedDistrictId: string;
  onSelectDistrict: (districtId: string) => void;
  mode: string;
}

// Bounding box for South India (Tamil Nadu, Kerala, Karnataka)
const SOUTH_INDIA_BOUNDS: [[number, number], [number, number]] = [
  [8.0, 74.0],  // South-West (Kanyakumari / Lakshadweep Sea)
  [18.6, 80.6]  // North-East (Bidar, Northern Karnataka / Bay of Bengal)
];

// Color mapping for continuous UTCI values
function getUtciContinuousColor(utci: number): [number, number, number, number] {
  // Returns [r, g, b, alpha]
  if (utci < 22) return [22, 163, 74, 215];        // #16a34a No thermal stress
  if (utci < 26) return [74, 222, 128, 220];       // #4ade80 Mild comfort
  if (utci < 32) return [234, 179, 8, 225];        // #eab308 Moderate heat stress
  if (utci < 38) return [234, 88, 12, 230];        // #ea580c Strong heat stress
  if (utci < 46) return [220, 38, 38, 235];        // #dc2626 Very strong heat stress
  return [153, 27, 27, 240];                       // #991b1b Extreme heat stress
}

export const GisMap: React.FC<GisMapProps> = ({
  districts,
  selectedDistrictId,
  onSelectDistrict,
  mode
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const geoJsonLayerRef = useRef<L.GeoJSON | null>(null);
  const thermalFieldLayerRef = useRef<L.ImageOverlay | null>(null);
  const boundsRef = useRef<L.LatLngBounds | null>(null);
  const geoJsonDataCacheRef = useRef<any | null>(null);

  // Visualization mode: 'district' (authoritative polygons) | 'field' (interpolated spatial field)
  const [vizMode, setVizMode] = useState<'district' | 'field'>('district');

  // Map of district ID -> DistrictSummary
  const districtMap = useMemo(() => {
    const map = new Map<string, DistrictSummary>();
    districts.forEach(d => map.set(d.id, d));
    return map;
  }, [districts]);

  // Generate IDW Interpolated Thermal Field Raster
  const generateThermalFieldDataUrl = useMemo(() => {
    if (districts.length === 0) return null;

    const canvas = document.createElement('canvas');
    const width = 140;
    const height = 180;
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const imgData = ctx.createImageData(width, height);
    const data = imgData.data;

    // Collect valid district centroids and their UTCI values
    const points: { lat: number; lon: number; utci: number }[] = [];
    districts.forEach(d => {
      const isUnavailable = d.thermal?.data_quality === 'UNAVAILABLE' || d.thermal?.utci_c === null || d.thermal?.utci_c === undefined;
      if (d.latitude && d.longitude && !isUnavailable && typeof d.thermal?.utci_c === 'number') {
        points.push({
          lat: d.latitude,
          lon: d.longitude,
          utci: d.thermal.utci_c
        });
      }
    });

    if (points.length === 0) return null;

    const [minLat, minLon] = SOUTH_INDIA_BOUNDS[0];
    const [maxLat, maxLon] = SOUTH_INDIA_BOUNDS[1];
    const pPower = 2.0;

    for (let py = 0; py < height; py++) {
      const lat = maxLat - (py / (height - 1)) * (maxLat - minLat);
      for (let px = 0; px < width; px++) {
        const lon = minLon + (px / (width - 1)) * (maxLon - minLon);

        let weightSum = 0;
        let utciSum = 0;
        let minDist = 999;

        for (let i = 0; i < points.length; i++) {
          const pt = points[i];
          const dLat = lat - pt.lat;
          const dLon = lon - pt.lon;
          const dist = Math.sqrt(dLat * dLat + dLon * dLon);

          if (dist < minDist) minDist = dist;

          if (dist < 0.01) {
            utciSum = pt.utci;
            weightSum = 1;
            break;
          }

          const w = 1.0 / Math.pow(dist + 0.08, pPower);
          weightSum += w;
          utciSum += w * pt.utci;
        }

        const interpolatedUtci = weightSum > 0 ? utciSum / weightSum : 28.0;
        const [r, g, b, alpha] = getUtciContinuousColor(interpolatedUtci);

        // Distance attenuation mask so ocean/far areas fade smoothly
        const distFade = minDist > 2.2 ? Math.max(0, 1.0 - (minDist - 2.2) * 1.5) : 1.0;
        const pixelIndex = (py * width + px) * 4;

        data[pixelIndex] = r;
        data[pixelIndex + 1] = g;
        data[pixelIndex + 2] = b;
        data[pixelIndex + 3] = Math.round(alpha * distFade);
      }
    }

    ctx.putImageData(imgData, 0, 0);
    return canvas.toDataURL();
  }, [districts]);

  // 1. Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Centered initially on South India
    const map = L.map(mapContainerRef.current, {
      center: [12.8, 77.5],
      zoom: 6.5,
      minZoom: 5.5,
      maxZoom: 12,
      scrollWheelZoom: true,
      zoomControl: false
    });

    // Custom Top-Right Zoom Control
    L.control.zoom({ position: 'topright' }).addTo(map);

    // Clean OpenStreetMap Tile Source (no CARTO API key requirement)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
      maxZoom: 18,
      opacity: 0.95
    }).addTo(map);

    mapInstanceRef.current = map;

    // Invalidate map size on container resize
    const resizeObserver = new ResizeObserver(() => {
      map.invalidateSize();
    });
    if (mapContainerRef.current) {
      resizeObserver.observe(mapContainerRef.current);
    }

    // Initial size invalidation
    setTimeout(() => {
      map.invalidateSize();
    }, 200);

    return () => {
      resizeObserver.disconnect();
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // 2. Fetch and Render District Polygons with Dynamic Bounds & Thermal Modes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const renderGeoJson = (geojsonData: any) => {
      geoJsonDataCacheRef.current = geojsonData;

      // Remove existing thermal field overlay if present
      if (thermalFieldLayerRef.current) {
        map.removeLayer(thermalFieldLayerRef.current);
        thermalFieldLayerRef.current = null;
      }

      // If Mode 2: Thermal Field is active, add raster image overlay under polygons
      if (vizMode === 'field' && generateThermalFieldDataUrl) {
        const fieldOverlay = L.imageOverlay(
          generateThermalFieldDataUrl,
          SOUTH_INDIA_BOUNDS,
          { opacity: 0.82, interactive: false }
        );
        fieldOverlay.addTo(map);
        thermalFieldLayerRef.current = fieldOverlay;
      }

      // Remove previous polygon layer
      if (geoJsonLayerRef.current) {
        map.removeLayer(geoJsonLayerRef.current);
      }

      // Build authoritative GeoJSON Layer
      const geoJsonLayer = L.geoJSON(geojsonData, {
        style: (feature) => {
          const dId = feature?.properties?.id;
          const summary = districtMap.get(dId);
          const isSelected = dId === selectedDistrictId;
          const isUnavailable = !summary || summary.thermal?.data_quality === 'UNAVAILABLE' || summary.thermal?.utci_c === null || summary.thermal?.utci_c === undefined;
          const catColor = isUnavailable ? '#94a3b8' : (summary?.thermal?.category_info?.color || '#16a34a');

          if (vizMode === 'field') {
            // In Thermal Field mode, polygons provide subtle contextual borders
            return {
              fillColor: catColor,
              weight: isSelected ? 3.5 : 1.2,
              opacity: 1,
              color: isSelected ? '#0f172a' : '#334155',
              dashArray: isSelected ? '' : '1',
              fillOpacity: isSelected ? 0.40 : 0.10
            };
          }

          // In Mode 1: District Risk (Authoritative Choropleth)
          return {
            fillColor: catColor,
            weight: isSelected ? 3.5 : 1.2,
            opacity: 1,
            color: isSelected ? '#0f172a' : '#334155',
            dashArray: isSelected ? '' : '',
            fillOpacity: isSelected ? 0.95 : (isUnavailable ? 0.70 : 0.85)
          };
        },
        onEachFeature: (feature, layer) => {
          const dId = feature?.properties?.id;
          const dName = feature?.properties?.name;
          const dState = feature?.properties?.state;
          const summary = districtMap.get(dId);

          const isUnavailable = !summary || summary.thermal?.data_quality === 'UNAVAILABLE' || summary.thermal?.utci_c === null || summary.thermal?.utci_c === undefined;
          const utciVal = isUnavailable ? 'No live data' : `${summary.thermal.utci_c.toFixed(1)}°C`;
          const catName = isUnavailable ? 'No live data' : (summary?.thermal?.category_info?.category || 'No thermal stress');
          const catColor = isUnavailable ? '#64748b' : (summary?.thermal?.category_info?.color || '#16a34a');
          const badgeBg = isUnavailable ? '#f1f5f9' : (summary?.thermal?.category_info?.badge_bg || '#f0fdf4');
          const tempVal = (!isUnavailable && summary?.weather?.temperature_c != null) ? `${summary.weather.temperature_c.toFixed(1)}°C` : 'N/A';
          const mrtVal = (!isUnavailable && summary?.thermal?.mrt_c != null) ? `${summary.thermal.mrt_c.toFixed(1)}°C` : 'N/A';
          const timeVal = summary?.timestamp_ist || 'Live';
          const dataQuality = isUnavailable ? 'UNAVAILABLE' : (summary?.thermal?.data_quality || 'VALID');

          // High-Aesthetic Tooltip
          layer.bindTooltip(`
            <div style="font-family: Inter, system-ui, sans-serif; font-size: 12px; min-width: 170px;">
              <div style="display: flex; align-items: center; justify-content: space-between; gap: 6px;">
                <span style="font-weight: 800; color: #0f172a; font-size: 13px;">${dName}</span>
                <span style="font-size: 9px; font-weight: 700; padding: 1px 4px; border-radius: 4px; background: #e2e8f0; color: #334155;">${dState}</span>
              </div>

              <div style="margin-top: 6px; padding: 4px 6px; border-radius: 6px; background: ${badgeBg}; border: 1px solid ${catColor}40; display: flex; align-items: center; justify-content: space-between;">
                <span style="font-size: 11px; font-weight: 700; color: ${catColor};">UTCI: ${utciVal}</span>
                <span style="font-size: 10px; font-weight: 600; color: ${catColor};">${catName}</span>
              </div>

              <div style="margin-top: 5px; display: flex; justify-content: space-between; font-size: 10px; color: #64748b;">
                <span>Air: <strong>${tempVal}</strong></span>
                <span>MRT: <strong>${mrtVal}</strong></span>
              </div>

              <div style="margin-top: 4px; padding-top: 3px; border-top: 1px solid #f1f5f9; display: flex; justify-content: space-between; font-size: 9px; color: #94a3b8;">
                <span>Status: ${dataQuality}</span>
                <span>${timeVal}</span>
              </div>
            </div>
          `, { sticky: true, className: 'custom-district-tooltip' });

          // Interactive Listeners
          layer.on({
            click: () => {
              onSelectDistrict(dId);
            },
            mouseover: (e) => {
              const target = e.target;
              if (dId !== selectedDistrictId) {
                target.setStyle({
                  weight: 2.5,
                  color: '#1e293b',
                  fillOpacity: vizMode === 'field' ? 0.35 : 0.95
                });
              }
            },
            mouseout: (e) => {
              geoJsonLayer.resetStyle(e.target);
              if (dId === selectedDistrictId) {
                e.target.setStyle({
                  weight: 3.5,
                  color: '#0f172a',
                  fillOpacity: vizMode === 'field' ? 0.40 : 0.92
                });
              }
            }
          });
        }
      }).addTo(map);

      geoJsonLayerRef.current = geoJsonLayer;

      // Fit map tightly to the 83 South Indian districts dynamically
      if (!boundsRef.current) {
        const bounds = geoJsonLayer.getBounds();
        if (bounds.isValid()) {
          boundsRef.current = bounds;
          map.fitBounds(bounds, { padding: [16, 16], maxZoom: 8 });
        }
      }
    };

    if (geoJsonDataCacheRef.current) {
      renderGeoJson(geoJsonDataCacheRef.current);
    } else {
      const geojsonPath = `${import.meta.env.BASE_URL.replace(/\/+$/, '')}/data/south_india_districts.geojson`;
      fetch(geojsonPath)
        .then(res => res.json())
        .then(geojsonData => {
          renderGeoJson(geojsonData);
        })
        .catch(err => console.error('Error loading GeoJSON:', err));
    }
  }, [districts, selectedDistrictId, onSelectDistrict, vizMode, districtMap, generateThermalFieldDataUrl]);

  // Re-fit View Handler
  const handleResetFraming = () => {
    const map = mapInstanceRef.current;
    if (map && boundsRef.current) {
      map.fitBounds(boundsRef.current, { padding: [16, 16], maxZoom: 8 });
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm flex flex-col relative z-10 isolate">
      
      {/* Map Header Controls Bar */}
      <div className="p-3.5 border-b border-slate-200 bg-slate-50/80 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-1.5 tracking-tight">
              <Compass className="w-4 h-4 text-teal-600" />
              GIS THERMAL RISK MAP
            </h2>
            <span className="text-[10px] px-2 py-0.5 rounded font-mono font-bold uppercase bg-teal-100 text-teal-900 border border-teal-200">
              UTCI (°C)
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            South India Geographic Coverage: <strong>83 Districts</strong> (TN 38 • KL 14 • KA 31)
          </p>
          {districts.some(d => d.thermal?.data_quality?.startsWith('SNAPSHOT')) && (
            <div className="mt-1 flex items-center gap-1.5">
              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                ● Snapshot Active ({districts.find(d => d.thermal?.data_quality?.startsWith('SNAPSHOT'))?.timestamp_ist || 'Recent'})
              </span>
            </div>
          )}
        </div>

        {/* Visualization Mode Segmented Controls */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          
          <div className="inline-flex rounded-lg border border-slate-300 p-0.5 bg-white shadow-xs text-xs font-semibold">
            <button
              type="button"
              onClick={() => setVizMode('district')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-colors ${
                vizMode === 'district'
                  ? 'bg-teal-700 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
              title="Authoritative 83-district choropleth based on representative observation calculations"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>District Risk</span>
            </button>

            <button
              type="button"
              onClick={() => setVizMode('field')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-colors ${
                vizMode === 'field'
                  ? 'bg-teal-700 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
              title="Interpolated continuous thermal field derived via Inverse Distance Weighting"
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Thermal Field</span>
            </button>
          </div>

          <button
            type="button"
            onClick={handleResetFraming}
            className="p-1.5 text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 border border-slate-300 rounded-lg shadow-xs transition-colors"
            title="Reset viewport framing to South India (83 Districts)"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>

        </div>
      </div>

      {/* Mode 2 Explanatory Scientific Disclaimer Banner */}
      {vizMode === 'field' && (
        <div className="px-3.5 py-1.5 bg-blue-50 border-b border-blue-200 text-[11px] text-blue-900 flex items-center gap-2">
          <Info className="w-3.5 h-3.5 text-blue-600 shrink-0" />
          <span>
            <strong>Spatial Interpolation Notice:</strong> Continuous thermal field estimated via Inverse Distance Weighting (IDW) from 83 district observations. District boundaries and calculated UTCI values remain authoritative.
          </span>
        </div>
      )}

      {/* Primary Map Canvas Container */}
      <div className="relative w-full h-[540px] lg:h-[580px] bg-slate-100 overflow-hidden">
        <div ref={mapContainerRef} className="w-full h-full" />

        {/* Map Legend Overlay */}
        <div className="absolute bottom-3 right-3 z-20 bg-white/95 backdrop-blur-sm p-2.5 sm:p-3 rounded-xl border border-slate-200 shadow-md text-xs pointer-events-auto max-w-[210px]">
          <div className="font-bold text-slate-900 mb-1.5 flex items-center justify-between border-b border-slate-100 pb-1">
            <span className="text-[11px] font-bold">UTCI THERMAL STRESS</span>
            <span className="text-[9px] text-slate-500 font-mono">Brode et al.</span>
          </div>

          <div className="space-y-1 text-[10px] sm:text-[11px]">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-[#991b1b] shrink-0 border border-slate-300" />
              <span className="text-slate-800 font-medium">Extreme heat stress</span>
              <span className="text-slate-600 ml-auto font-mono text-[9px] font-semibold">&gt; 46°C</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-[#dc2626] shrink-0 border border-slate-300" />
              <span className="text-slate-800 font-medium">Very strong heat</span>
              <span className="text-slate-600 ml-auto font-mono text-[9px] font-semibold">38–46°C</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-[#ea580c] shrink-0 border border-slate-300" />
              <span className="text-slate-800 font-medium">Strong heat stress</span>
              <span className="text-slate-600 ml-auto font-mono text-[9px] font-semibold">32–38°C</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-[#eab308] shrink-0 border border-slate-300" />
              <span className="text-slate-800 font-medium">Moderate heat</span>
              <span className="text-slate-600 ml-auto font-mono text-[9px] font-semibold">26–32°C</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-[#16a34a] shrink-0 border border-slate-300" />
              <span className="text-slate-800 font-medium">No thermal stress</span>
              <span className="text-slate-600 ml-auto font-mono text-[9px] font-semibold">&lt; 26°C</span>
            </div>
          </div>

          {/* Continuous Gradient Bar when in Thermal Field mode */}
          {vizMode === 'field' && (
            <div className="mt-2 pt-1.5 border-t border-slate-100">
              <div className="text-[9px] font-semibold text-slate-500 mb-0.5">Interpolated Color Scale:</div>
              <div
                className="h-2 w-full rounded-sm border border-slate-300"
                style={{
                  background: 'linear-gradient(to right, #16a34a, #4ade80, #eab308, #ea580c, #dc2626, #991b1b)'
                }}
              />
              <div className="flex justify-between text-[8px] font-mono text-slate-500 mt-0.5">
                <span>&lt; 22°C</span>
                <span>32°C</span>
                <span>&gt; 46°C</span>
              </div>
            </div>
          )}
        </div>

        {/* Top-Left Geographic Orientation Badge */}
        <div className="absolute top-3 left-3 z-20 bg-white/90 backdrop-blur-sm px-2.5 py-1 rounded-lg border border-slate-200 text-[11px] font-semibold text-slate-800 shadow-xs pointer-events-none flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-teal-600 animate-pulse" />
          <span>Click any of the 83 districts to inspect human thermal load</span>
        </div>

      </div>

    </div>
  );
};
export default GisMap;

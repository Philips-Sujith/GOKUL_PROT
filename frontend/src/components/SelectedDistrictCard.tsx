import React from 'react';
import { 
  Thermometer, 
  Sun, 
  Wind, 
  Droplets, 
  Activity, 
  Clock, 
  Compass, 
  Gauge, 
  AlertTriangle,
  HelpCircle,
  UserCheck
} from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { DistrictSummary, UTCICategoryInfo } from '../types';
import { HumanThermalAvatar } from './HumanThermalAvatar';
import { ThreeDayForecastCard } from './ThreeDayForecastCard';

interface SelectedDistrictCardProps {
  district: DistrictSummary | null;
  historyTrend: any[];
}

export const SelectedDistrictCard: React.FC<SelectedDistrictCardProps> = ({
  district,
  historyTrend
}) => {
  if (!district) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500 shadow-sm">
        <Activity className="w-12 h-12 mx-auto text-slate-300 mb-3" />
        <p className="font-medium text-slate-700">Select a district on the map or list</p>
        <p className="text-xs text-slate-400 mt-1">Detailed physical thermal parameters will render here.</p>
      </div>
    );
  }

  const { thermal, weather, name, state, timestamp_ist } = district;
  const isUnavailable = thermal?.data_quality === 'UNAVAILABLE' || thermal?.utci_c == null;
  const utciCat: UTCICategoryInfo = isUnavailable ? {
    category: 'No live data',
    min_utci: 0,
    max_utci: 0,
    severity_rank: 0,
    color: '#94a3b8',
    badge_bg: '#f1f5f9',
    badge_text: '#475569',
    badge_border: '#cbd5e1',
    description: 'Meteorological and thermal observation data for this district is currently unavailable from external providers.'
  } : thermal.category_info;

  // Radiation delta (MRT minus Air Temp)
  const radiationDelta = (thermal?.mrt_c != null && weather?.temperature_c != null) ? (thermal.mrt_c - weather.temperature_c) : 0;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-5">
      
      {/* Header Info */}
      <div className="flex items-start justify-between border-b border-slate-100 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-900">{name}</h2>
            <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium border border-slate-200">
              {state}
            </span>
            {district.scenario && (
              <span className="text-xs px-2 py-0.5 rounded bg-amber-50 text-amber-800 font-medium border border-amber-200">
                {district.scenario}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1">
            <Clock className="w-3 h-3 text-slate-400" />
            Observation: {timestamp_ist}
          </p>
        </div>

        {/* Quality status */}
        <div className="flex flex-col items-end gap-1">
          <span className={`text-[11px] px-2 py-0.5 rounded-full font-semibold border ${
            isUnavailable
              ? 'bg-slate-100 text-slate-600 border-slate-300'
              : thermal.data_quality === 'VALID'
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
              : 'bg-amber-50 text-amber-700 border-amber-200'
          }`}>
            ● {isUnavailable ? 'No live data' : (thermal.data_quality || 'VALID')}
          </span>
          {thermal.data_quality?.startsWith('SNAPSHOT') && (
            <span className="text-[10px] text-amber-700 font-medium">
              Snapshot time: {timestamp_ist}
            </span>
          )}
        </div>
      </div>

      {/* Hero Metric: UTCI & Human Thermal Stress Visual */}
      <div className="space-y-4">
        
        {/* Primary UTCI Hero Value + Human Avatar Representation */}
        <div className="bg-slate-50/80 rounded-xl p-4 border border-slate-200 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-2">
            <span className="flex items-center gap-1.5 font-bold tracking-wide text-slate-700">
              <Thermometer className="w-4 h-4 text-teal-600" />
              CURRENT HUMAN THERMAL STRESS
            </span>
            <span title="Universal Thermal Climate Index calculated via ECMWF thermofeel polynomial" className="cursor-help text-slate-400">
              <HelpCircle className="w-3.5 h-3.5" />
            </span>
          </div>

          <div className="flex flex-col sm:flex-row items-center sm:items-stretch justify-between gap-4 pt-1">
            {/* LEFT REGION (58% width on desktop) */}
            <div className="w-full sm:w-[58%] flex flex-col justify-between space-y-2.5">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                  CALCULATED UTCI
                </span>
                <div className="flex items-baseline gap-2 mt-0.5">
                  <span className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight font-mono">
                    {isUnavailable || thermal.utci_c == null ? '--' : thermal.utci_c.toFixed(1)}
                  </span>
                  <span className="text-lg font-bold text-slate-500">°C</span>
                </div>
              </div>
              
              <div>
                <span 
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold border"
                  style={{
                    backgroundColor: utciCat?.badge_bg || '#f1f5f9',
                    color: utciCat?.badge_text || '#475569',
                    borderColor: utciCat?.badge_border || '#cbd5e1'
                  }}
                >
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                  <span>{utciCat?.category || 'No live data'}</span>
                </span>
              </div>
              
              <p className="text-xs text-slate-600 font-medium leading-relaxed">
                {isUnavailable ? 'Live meteorological feed temporarily unavailable.' : `Current conditions indicate ${utciCat?.category?.toLowerCase() || 'thermal strain'}.`}
              </p>
            </div>

            {/* RIGHT REGION (42% width on desktop) */}
            <div className="w-full sm:w-[42%] flex justify-center items-center">
              <HumanThermalAvatar
                utci={isUnavailable || thermal.utci_c == null ? 0 : thermal.utci_c}
                categoryName={isUnavailable ? 'No live data' : (utciCat?.category || 'Moderate')}
                className="w-full"
              />
            </div>
          </div>
        </div>

        {/* Category Description & Scientific Explanation */}
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-teal-600" />
              Physiological Heat Burden
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              {utciCat?.description}
            </p>
          </div>

          <div className="mt-3 pt-3 border-t border-slate-100 grid grid-cols-2 gap-2 text-xs">
            <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200/60">
              <span className="text-slate-500 block text-[11px] font-medium">Mean Radiant Temp (MRT):</span>
              <strong className="text-slate-900 font-bold text-sm">
                {isUnavailable || thermal.mrt_c == null ? '--' : `${thermal.mrt_c.toFixed(1)}°C`}
              </strong>
              <span className="text-[10px] text-teal-700 font-medium block mt-0.5">
                {isUnavailable ? 'Awaiting station feed' : `(+${radiationDelta > 0 ? radiationDelta.toFixed(1) : '0.0'}°C radiation load)`}
              </span>
            </div>
            <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200/60">
              <span className="text-slate-500 block text-[11px] font-medium">Ambient Air Temp:</span>
              <strong className="text-slate-900 font-bold text-sm">
                {isUnavailable || weather.temperature_c == null ? '--' : `${weather.temperature_c.toFixed(1)}°C`}
              </strong>
              <span className="text-[10px] text-slate-500 font-medium block mt-0.5">
                2m dry bulb thermometer
              </span>
            </div>
          </div>
        </div>

      </div>

      {/* Feature 2: 3-Day Human Thermal Stress Forecast Outlook */}
      <ThreeDayForecastCard
        districtId={district.id}
        districtName={district.name}
      />

      {/* Environmental Metrics Grid */}
      <div>
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
          Underlying Environmental & Radiation Conditions
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Droplets className="w-3.5 h-3.5 text-blue-500" />
              <span>Rel. Humidity</span>
            </div>
            <div className="text-base font-bold text-slate-900">
              {weather.relative_humidity != null ? `${weather.relative_humidity.toFixed(0)}%` : '--'}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              Moisture retards sweat evaporation
            </div>
          </div>

          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Wind className="w-3.5 h-3.5 text-teal-600" />
              <span>Wind (10m)</span>
            </div>
            <div className="text-base font-bold text-slate-900">
              {weather.wind_speed_mps != null ? `${weather.wind_speed_mps.toFixed(1)} m/s` : '--'}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              Convective air movement
            </div>
          </div>

          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Sun className="w-3.5 h-3.5 text-amber-500" />
              <span>Solar Irradiance</span>
            </div>
            <div className="text-base font-bold text-slate-900">
              {weather.shortwave_radiation_wm2 != null ? `${weather.shortwave_radiation_wm2.toFixed(0)} W/m²` : '--'}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              Direct & diffuse downwelling flux
            </div>
          </div>

          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
            <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium mb-1">
              <Gauge className="w-3.5 h-3.5 text-indigo-500" />
              <span>Surface Pressure</span>
            </div>
            <div className="text-base font-bold text-slate-900">
              {weather.surface_pressure_hpa != null ? `${weather.surface_pressure_hpa.toFixed(0)} hPa` : '--'}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              Barometric reading
            </div>
          </div>

        </div>
      </div>

      {/* Historical Trend Chart (Recharts) */}
      {historyTrend && historyTrend.length > 0 && (
        <div className="border-t border-slate-100 pt-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-teal-600" />
              Thermal Stress Evolution (Recent Observations)
            </h3>
            <span className="text-[11px] text-slate-500 font-mono">UTCI vs MRT (°C)</span>
          </div>

          <div className="h-40 w-full bg-slate-50/50 rounded-lg p-2 border border-slate-200/70">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={historyTrend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="utciGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0d9488" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0d9488" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="timestamp_ist" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis domain={['dataMin - 2', 'dataMax + 2']} tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    borderColor: '#cbd5e1',
                    borderRadius: '8px',
                    fontSize: '12px'
                  }}
                />
                <Area type="monotone" dataKey="utci_c" name="UTCI (°C)" stroke="#0d9488" strokeWidth={2} fillOpacity={1} fill="url(#utciGradient)" />
                <Area type="monotone" dataKey="mrt_c" name="MRT (°C)" stroke="#ea580c" strokeWidth={1.5} strokeDasharray="3 3" fill="none" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Scientific Calculation Chain & Debug Inspector */}
      <div className="border-t border-slate-100 pt-3 text-xs">
        <details className="group rounded-lg border border-slate-200 bg-slate-50/70 p-3">
          <summary className="font-bold text-slate-700 cursor-pointer flex items-center justify-between list-none">
            <span className="flex items-center gap-1.5 text-teal-800">
              <Activity className="w-3.5 h-3.5 text-teal-600" />
              Scientific Thermal Calculation Chain (ECMWF thermofeel)
            </span>
            <span className="text-[10px] text-slate-500 font-mono group-open:rotate-180 transition-transform">
              ▼
            </span>
          </summary>
          
          <div className="mt-3 space-y-2 text-[11px] text-slate-600 border-t border-slate-200/60 pt-2 font-mono">
            <div className="flex justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">1. Atmospheric Vapour Pressure:</span>
              <span className="text-slate-900 font-semibold">
                {(weather.relative_humidity != null && weather.temperature_c != null)
                  ? `${((weather.relative_humidity / 100.0) * 6.112 * Math.exp((17.67 * weather.temperature_c) / (weather.temperature_c + 243.5))).toFixed(2)} hPa (Magnus-Tetens)`
                  : '--'}
              </span>
            </div>
            <div className="flex justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">2. Solar Downwelling (SSRD / Direct):</span>
              <span className="text-slate-900 font-semibold">
                {weather.shortwave_radiation_wm2 != null ? `${weather.shortwave_radiation_wm2.toFixed(0)} W/m² (Direct: ${(weather.direct_radiation_wm2 || 0).toFixed(0)})` : '--'}
              </span>
            </div>
            <div className="flex justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">3. Mean Radiant Temperature (MRT):</span>
              <span className="text-slate-900 font-semibold">
                {thermal.mrt_c != null ? `${thermal.mrt_c.toFixed(2)}°C / ${(thermal.mrt_c + 273.15).toFixed(2)} K (Di Napoli et al. 2020)` : '--'}
              </span>
            </div>
            <div className="flex justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">4. Wind at 10m -&gt; 2m (v_a):</span>
              <span className="text-slate-900 font-semibold">
                {weather.wind_speed_mps != null ? `${weather.wind_speed_mps.toFixed(2)} m/s (clamped to physical bounds)` : '--'}
              </span>
            </div>
            <div className="flex justify-between py-0.5 border-b border-slate-100">
              <span className="text-slate-500">5. 6th-Order Polynomial Output (UTCI):</span>
              <span className="text-teal-700 font-bold">
                {thermal.utci_c != null ? `${thermal.utci_c.toFixed(2)}°C (Brode et al. 2012)` : '--'}
              </span>
            </div>
            <div className="flex justify-between py-0.5">
              <span className="text-slate-500">6. Authoritative Category:</span>
              <span className="font-bold" style={{ color: utciCat?.color || '#0f172a' }}>
                {utciCat?.category} {utciCat?.severity_rank ? `(Rank ${utciCat.severity_rank})` : ''}
              </span>
            </div>
          </div>
        </details>
      </div>

    </div>
  );
};

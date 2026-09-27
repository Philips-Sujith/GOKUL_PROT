import React, { useEffect, useState } from 'react';
import { Calendar, Clock, AlertTriangle, RefreshCw, Info, ArrowUpRight } from 'lucide-react';
import { DistrictForecastData } from '../types';
import { fetchDistrictForecast } from '../services/api';

interface ThreeDayForecastCardProps {
  districtId: string;
  districtName: string;
}

export const ThreeDayForecastCard: React.FC<ThreeDayForecastCardProps> = ({
  districtId,
  districtName
}) => {
  const [forecast, setForecast] = useState<DistrictForecastData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    fetchDistrictForecast(districtId)
      .then(res => {
        if (isMounted) {
          setForecast(res.forecast);
          setLoading(false);
        }
      })
      .catch(err => {
        if (isMounted) {
          setError(err.message || 'Forecast unavailable');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [districtId]);

  if (loading) {
    return (
      <div className="bg-slate-50/60 rounded-xl border border-slate-200 p-4 text-center">
        <div className="flex items-center justify-center gap-2 text-xs font-semibold text-slate-500">
          <RefreshCw className="w-3.5 h-3.5 animate-spin text-teal-600" />
          <span>Computing 3-day thermofeel forecast for {districtName}...</span>
        </div>
      </div>
    );
  }

  if (error || !forecast || !forecast.days || forecast.days.length === 0) {
    return (
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-4 text-center text-xs text-slate-500">
        <p className="font-semibold text-slate-600">3-Day Forecast Unavailable</p>
        <p className="text-[11px] text-slate-400 mt-0.5">Could not retrieve physical forecast parameters at this time.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-2">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-teal-700" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900">
            3-Day Human Thermal Stress Outlook
          </h3>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-400">
          <span>Updated: {forecast.forecast_generated_at || 'Just now'}</span>
          {forecast.data_quality === 'STALE' && (
            <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-bold">
              STALE
            </span>
          )}
        </div>
      </div>

      {/* 3 Days Grid */}
      <div className="grid grid-cols-3 gap-2.5">
        {forecast.days.map((day, idx) => {
          const cat = day.category_info;
          return (
            <div
              key={idx}
              className="bg-slate-50/80 rounded-lg p-3 border border-slate-200 flex flex-col justify-between hover:bg-slate-100/70 transition-colors"
            >
              {/* Day Label & Date */}
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-extrabold text-slate-800 uppercase tracking-tight">
                    {day.day_label}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {day.date ? day.date.slice(5) : ''}
                  </span>
                </div>

                {/* Peak UTCI Value */}
                <div className="mt-2 flex items-baseline gap-1">
                  <span className="text-2xl font-black text-slate-900 tracking-tight">
                    {day.peak_utci_c.toFixed(1)}
                  </span>
                  <span className="text-xs font-bold text-slate-500">°C</span>
                </div>

                {/* Approximate Peak Time */}
                <div className="text-[10px] text-slate-500 flex items-center gap-1 mt-0.5 font-medium">
                  <Clock className="w-3 h-3 text-slate-400" />
                  <span>Around {day.peak_time_ist}</span>
                </div>
              </div>

              {/* Category Badge */}
              <div className="mt-2.5 pt-2 border-t border-slate-200/60">
                <span
                  className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border leading-tight w-full justify-center text-center"
                  style={{
                    backgroundColor: cat?.badge_bg || '#fef2f2',
                    color: cat?.badge_text || '#991b1b',
                    borderColor: cat?.badge_border || '#fecaca'
                  }}
                >
                  <AlertTriangle className="w-2.5 h-2.5 shrink-0" />
                  <span className="truncate">{cat?.category || 'No Stress'}</span>
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Advisory narrative outlook */}
      {forecast.outlook_summary && (
        <div className="p-2.5 bg-teal-50/60 rounded-lg border border-teal-100 text-xs text-teal-900 flex items-start gap-2">
          <Info className="w-3.5 h-3.5 text-teal-700 shrink-0 mt-0.5" />
          <p className="leading-snug font-medium">
            {forecast.outlook_summary}
          </p>
        </div>
      )}
    </div>
  );
};

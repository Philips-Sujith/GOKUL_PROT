import React, { useEffect, useState, useMemo } from 'react';
import { 
  TrendingUp, 
  Clock, 
  AlertTriangle, 
  RefreshCw, 
  Activity, 
  Calendar,
  Thermometer,
  Info
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid, 
  ReferenceLine 
} from 'recharts';
import { DistrictForecastData } from '../types';
import { fetchDistrictForecast } from '../services/api';

interface SeventyTwoHourTrendCardProps {
  districtId: string;
  districtName: string;
}

interface TimelinePoint {
  index: number;
  timeLabel: string;
  fullTime: string;
  dayLabel: string;
  utci_c: number;
  temp_c: number;
  category: string;
}

export const SeventyTwoHourTrendCard: React.FC<SeventyTwoHourTrendCardProps> = ({
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

  // Construct continuous 72-hour timeline from the existing forecast dataset
  const { timelineData, peakPoint, overallPeakCategory } = useMemo(() => {
    if (!forecast || !forecast.days || forecast.days.length === 0) {
      return { timelineData: [], peakPoint: null, overallPeakCategory: null };
    }

    const points: TimelinePoint[] = [];
    let idx = 0;

    forecast.days.forEach(day => {
      const dayName = day.day_label; // "Today", "Tomorrow", "Day 3"
      const shortDay = dayName === 'Today' ? 'Today' : dayName === 'Tomorrow' ? 'Tmrw' : 'Day 3';
      
      if (day.hourly_summary && day.hourly_summary.length > 0) {
        day.hourly_summary.forEach(h => {
          points.push({
            index: idx++,
            timeLabel: `${shortDay} ${h.time_ist}`,
            fullTime: `${dayName} at ${h.time_ist} IST`,
            dayLabel: dayName,
            utci_c: h.utci_c,
            temp_c: h.temp_c,
            category: h.category
          });
        });
      } else {
        // Fallback to peak if hourly summary is unavailable
        points.push({
          index: idx++,
          timeLabel: `${shortDay} ${day.peak_time_ist}`,
          fullTime: `${dayName} around ${day.peak_time_ist}`,
          dayLabel: dayName,
          utci_c: day.peak_utci_c,
          temp_c: day.peak_temperature_c || day.peak_utci_c - 2,
          category: day.category_info?.category || 'Moderate heat stress'
        });
      }
    });

    // Find the absolute highest peak in the 72-hour period
    let maxPt: TimelinePoint | null = null;
    if (points.length > 0) {
      maxPt = points.reduce((prev, curr) => (curr.utci_c > prev.utci_c ? curr : prev), points[0]);
    }

    // Identify corresponding category badge styling
    const peakDay = forecast.days.reduce((prev, curr) => 
      (curr.peak_utci_c > prev.peak_utci_c ? curr : prev), forecast.days[0]
    );

    return { 
      timelineData: points, 
      peakPoint: maxPt, 
      overallPeakCategory: peakDay?.category_info || null 
    };
  }, [forecast]);

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm text-center">
        <div className="flex items-center justify-center gap-2 text-xs font-semibold text-slate-500 py-6">
          <RefreshCw className="w-4 h-4 animate-spin text-teal-600" />
          <span>Loading 72-hour heat stress projection for {districtName}...</span>
        </div>
      </div>
    );
  }

  if (error || !forecast || timelineData.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm text-center text-xs text-slate-500">
        <Activity className="w-8 h-8 text-slate-300 mx-auto mb-2" />
        <p className="font-semibold text-slate-700">72-Hour Heat Stress Trend Unavailable</p>
        <p className="text-[11px] text-slate-400 mt-0.5">Could not construct forecast sequence from the weather provider.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-sm space-y-4">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5 tracking-tight">
              <TrendingUp className="w-4 h-4 text-teal-600" />
              72-HOUR HEAT STRESS TREND
            </h3>
            <span className="text-[10px] px-2 py-0.5 rounded font-mono font-bold uppercase bg-teal-50 text-teal-800 border border-teal-200">
              {districtName}
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Forecast Universal Thermal Climate Index (UTCI) trajectory over the next 72 hours
          </p>
        </div>

        <div className="flex items-center gap-2 text-[11px] text-slate-400">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>Updated: {forecast.forecast_generated_at || 'Live'}</span>
        </div>
      </div>

      {/* Chart Area */}
      <div className="h-48 sm:h-52 w-full bg-slate-50/60 rounded-xl p-2.5 border border-slate-200/70">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={timelineData} margin={{ top: 12, right: 12, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="forecastUtciGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0d9488" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#0d9488" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            
            <XAxis 
              dataKey="timeLabel" 
              interval="preserveStartEnd"
              tick={{ fontSize: 10, fill: '#64748b' }}
              minTickGap={28}
            />
            
            <YAxis 
              domain={['auto', 'auto']} 
              tick={{ fontSize: 10, fill: '#64748b' }}
              unit="°"
            />

            {/* Critical UTCI threshold reference line */}
            <ReferenceLine 
              y={38.0} 
              stroke="#dc2626" 
              strokeDasharray="4 4" 
              label={{ 
                value: '38°C Strong Stress', 
                fill: '#dc2626', 
                fontSize: 9, 
                position: 'insideTopRight' 
              }} 
            />

            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload as TimelinePoint;
                  return (
                    <div className="bg-white/95 backdrop-blur-sm p-2.5 rounded-lg border border-slate-200 shadow-lg text-xs space-y-1">
                      <p className="font-bold text-slate-800">{data.fullTime}</p>
                      <div className="flex items-center gap-2 pt-1 border-t border-slate-100">
                        <span className="text-teal-700 font-extrabold font-mono text-sm">
                          UTCI: {data.utci_c.toFixed(1)}°C
                        </span>
                        <span className="text-[11px] text-slate-500 font-mono">
                          (Air: {data.temp_c.toFixed(1)}°C)
                        </span>
                      </div>
                      <p className="text-[10px] font-semibold text-slate-600">
                        Category: <span className="text-teal-800">{data.category}</span>
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />

            <Area 
              type="monotone" 
              dataKey="utci_c" 
              name="Forecast UTCI (°C)" 
              stroke="#0d9488" 
              strokeWidth={2.5} 
              fillOpacity={1} 
              fill="url(#forecastUtciGrad)" 
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Peak Highlight & Category Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 items-center pt-1 text-xs">
        {/* Peak Forecast Stat Box */}
        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
              72-Hour Peak Forecast
            </span>
            <div className="flex items-baseline gap-1 mt-0.5">
              <span className="text-2xl font-black text-slate-900 tracking-tight font-mono">
                {peakPoint ? peakPoint.utci_c.toFixed(1) : (forecast.days[0]?.peak_utci_c || 0).toFixed(1)}
              </span>
              <span className="text-xs font-bold text-slate-500">°C</span>
            </div>
          </div>

          <div className="text-right">
            <span className="text-[10px] text-slate-500 block font-medium">Expected Peak Timing</span>
            <strong className="text-slate-800 text-xs font-semibold block mt-0.5">
              {peakPoint ? peakPoint.fullTime : `${forecast.days[0]?.day_label} ${forecast.days[0]?.peak_time_ist}`}
            </strong>
          </div>
        </div>

        {/* Category Classification */}
        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
              Peak Thermal Stress Category
            </span>
            <div className="mt-1">
              <span 
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold border"
                style={{
                  backgroundColor: overallPeakCategory?.badge_bg || '#fef2f2',
                  color: overallPeakCategory?.badge_text || '#991b1b',
                  borderColor: overallPeakCategory?.badge_border || '#fecaca'
                }}
              >
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                <span>{overallPeakCategory?.category || 'Strong heat stress'}</span>
              </span>
            </div>
          </div>

          <div className="text-right text-[11px] text-slate-500 max-w-[130px] leading-tight">
            ECMWF thermofeel physics calculation
          </div>
        </div>
      </div>

    </div>
  );
};

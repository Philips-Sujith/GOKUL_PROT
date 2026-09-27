import React, { useEffect, useState, useMemo } from 'react';
import { 
  Calendar, 
  Search, 
  Filter, 
  Clock, 
  AlertTriangle, 
  ArrowUpDown, 
  RefreshCw,
  Send,
  CheckCircle,
  TrendingUp
} from 'lucide-react';
import { DistrictForecastOverviewItem, DayForecast } from '../types';
import { fetchAllForecasts } from '../services/api';

interface AdminForecastTableProps {
  onSelectDistrictForEscalation?: (districtId: string) => void;
  onRefreshTrigger?: () => void;
}

export const AdminForecastTable: React.FC<AdminForecastTableProps> = ({
  onSelectDistrictForEscalation
}) => {
  const [forecasts, setForecasts] = useState<DistrictForecastOverviewItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedState, setSelectedState] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [onlyHighRisk, setOnlyHighRisk] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<'name' | 'today' | 'tomorrow' | 'day3'>('tomorrow');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const loadData = () => {
    setLoading(true);
    fetchAllForecasts()
      .then(res => {
        setForecasts(res.forecasts || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching admin forecasts:', err);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredAndSortedForecasts = useMemo(() => {
    return forecasts
      .filter(f => {
        if (selectedState !== 'ALL' && f.state !== selectedState) return false;
        if (searchQuery.trim() && !f.district_name.toLowerCase().includes(searchQuery.toLowerCase())) {
          return false;
        }
        if (onlyHighRisk) {
          const hasHighRisk = f.days?.some(d => d.peak_utci_c >= 38.0);
          if (!hasHighRisk) return false;
        }
        return true;
      })
      .sort((a, b) => {
        let valA = 0;
        let valB = 0;

        if (sortBy === 'name') {
          return sortOrder === 'asc' 
            ? a.district_name.localeCompare(b.district_name)
            : b.district_name.localeCompare(a.district_name);
        } else if (sortBy === 'today') {
          valA = a.days?.[0]?.peak_utci_c || 0;
          valB = b.days?.[0]?.peak_utci_c || 0;
        } else if (sortBy === 'tomorrow') {
          valA = a.days?.[1]?.peak_utci_c || 0;
          valB = b.days?.[1]?.peak_utci_c || 0;
        } else if (sortBy === 'day3') {
          valA = a.days?.[2]?.peak_utci_c || 0;
          valB = b.days?.[2]?.peak_utci_c || 0;
        }

        return sortOrder === 'asc' ? valA - valB : valB - valA;
      });
  }, [forecasts, selectedState, searchQuery, onlyHighRisk, sortBy, sortOrder]);

  const handleSort = (field: 'name' | 'today' | 'tomorrow' | 'day3') => {
    if (sortBy === field) {
      setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const renderDayCell = (day?: DayForecast) => {
    if (!day) return <span className="text-slate-400 text-xs">N/A</span>;
    const cat = day.category_info;
    const isHigh = day.peak_utci_c >= 38.0;

    return (
      <div className="space-y-1">
        <div className="flex items-baseline gap-1">
          <span className={`text-sm font-extrabold font-mono ${isHigh ? 'text-rose-700' : 'text-slate-900'}`}>
            {day.peak_utci_c.toFixed(1)}°C
          </span>
          <span className="text-[10px] text-slate-400 font-medium">
            @{day.peak_time_ist.replace(' IST', '')}
          </span>
        </div>
        <div>
          <span
            className="inline-flex items-center gap-1 text-[9px] font-bold px-1.5 py-0.5 rounded border leading-none"
            style={{
              backgroundColor: cat?.badge_bg || '#fef2f2',
              color: cat?.badge_text || '#991b1b',
              borderColor: cat?.badge_border || '#fecaca'
            }}
          >
            {cat?.category || 'No stress'}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-teal-700" />
            <h3 className="text-sm font-bold text-slate-900">
              3-Day District Heat-Stress Forecast (83 Jurisdictions)
            </h3>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Physical ECMWF thermofeel MRT & UTCI projection across Today, Tomorrow, and Day 3
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadData}
            disabled={loading}
            className="text-xs font-semibold px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors flex items-center gap-1 border border-slate-200"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-teal-600' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="grid grid-cols-1 sm:grid-cols-12 gap-2.5 text-xs">
        {/* State Filter */}
        <div className="sm:col-span-3 flex items-center gap-1.5">
          <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <select
            value={selectedState}
            onChange={e => setSelectedState(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-800 focus:outline-none focus:ring-1 focus:ring-teal-500"
          >
            <option value="ALL">All States (83 Districts)</option>
            <option value="Tamil Nadu">Tamil Nadu (38)</option>
            <option value="Kerala">Kerala (14)</option>
            <option value="Karnataka">Karnataka (31)</option>
          </select>
        </div>

        {/* Search Input */}
        <div className="sm:col-span-4 relative">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Search district name..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-2.5 py-1.5 text-xs font-medium text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
        </div>

        {/* High Risk Only Toggle */}
        <div className="sm:col-span-5 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => setOnlyHighRisk(!onlyHighRisk)}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-colors flex items-center gap-1.5 border ${
              onlyHighRisk
                ? 'bg-rose-50 text-rose-700 border-rose-300'
                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
            <span>High Heat Stress Only (UTCI ≥ 38°C)</span>
          </button>
        </div>
      </div>

      {/* Forecast Table */}
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-50/90 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[11px]">
              <th 
                className="py-2.5 px-3 cursor-pointer hover:bg-slate-100 transition-colors"
                onClick={() => handleSort('name')}
              >
                <div className="flex items-center gap-1">
                  <span>District</span>
                  <ArrowUpDown className="w-3 h-3 text-slate-400" />
                </div>
              </th>
              <th 
                className="py-2.5 px-3 cursor-pointer hover:bg-slate-100 transition-colors"
                onClick={() => handleSort('today')}
              >
                <div className="flex items-center gap-1">
                  <span>Today Peak</span>
                  <ArrowUpDown className="w-3 h-3 text-slate-400" />
                </div>
              </th>
              <th 
                className="py-2.5 px-3 cursor-pointer hover:bg-slate-100 transition-colors"
                onClick={() => handleSort('tomorrow')}
              >
                <div className="flex items-center gap-1">
                  <span>Tomorrow Peak</span>
                  <ArrowUpDown className="w-3 h-3 text-slate-400" />
                </div>
              </th>
              <th 
                className="py-2.5 px-3 cursor-pointer hover:bg-slate-100 transition-colors"
                onClick={() => handleSort('day3')}
              >
                <div className="flex items-center gap-1">
                  <span>Day 3 Peak</span>
                  <ArrowUpDown className="w-3 h-3 text-slate-400" />
                </div>
              </th>
              {onSelectDistrictForEscalation && (
                <th className="py-2.5 px-3 text-right">Action</th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-400">
                  <div className="flex items-center justify-center gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-teal-600" />
                    <span>Loading 3-day forecasts for 83 districts...</span>
                  </div>
                </td>
              </tr>
            ) : filteredAndSortedForecasts.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-400">
                  No districts match the selected filter.
                </td>
              </tr>
            ) : (
              filteredAndSortedForecasts.map(f => (
                <tr key={f.district_id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-2.5 px-3 font-semibold text-slate-900">
                    <div>{f.district_name}</div>
                    <span className="text-[10px] text-slate-400 font-normal">{f.state}</span>
                  </td>
                  <td className="py-2.5 px-3">
                    {renderDayCell(f.days?.[0])}
                  </td>
                  <td className="py-2.5 px-3">
                    {renderDayCell(f.days?.[1])}
                  </td>
                  <td className="py-2.5 px-3">
                    {renderDayCell(f.days?.[2])}
                  </td>
                  {onSelectDistrictForEscalation && (
                    <td className="py-2.5 px-3 text-right">
                      <button
                        type="button"
                        onClick={() => onSelectDistrictForEscalation(f.district_id)}
                        className="text-[11px] font-semibold px-2 py-1 bg-teal-50 hover:bg-teal-100 text-teal-800 rounded border border-teal-200 transition-colors inline-flex items-center gap-1"
                      >
                        <Send className="w-3 h-3 text-teal-600" />
                        <span>Escalate</span>
                      </button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
        <span>Showing {filteredAndSortedForecasts.length} of {forecasts.length} districts</span>
        <span className="font-mono">ECMWF thermofeel physics pipeline • Open-Meteo hourly forecast</span>
      </div>
    </div>
  );
};

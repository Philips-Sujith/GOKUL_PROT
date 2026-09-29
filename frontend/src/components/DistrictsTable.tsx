import React, { useState, useMemo } from 'react';
import { Search, Filter, ArrowUpDown, ChevronRight } from 'lucide-react';
import { DistrictSummary } from '../types';

interface DistrictsTableProps {
  districts: DistrictSummary[];
  selectedDistrictId: string;
  onSelectDistrict: (districtId: string) => void;
}

export const DistrictsTable: React.FC<DistrictsTableProps> = ({
  districts,
  selectedDistrictId,
  onSelectDistrict
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedState, setSelectedState] = useState('ALL');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

  const filteredDistricts = useMemo(() => {
    return districts
      .filter((d) => {
        const matchesName = d.name.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesState = selectedState === 'ALL' || d.state === selectedState;
        return matchesName && matchesState;
      })
      .sort((a, b) => {
        const valA = (a.thermal?.data_quality !== 'UNAVAILABLE' && a.thermal?.utci_c != null) ? a.thermal.utci_c : -999;
        const valB = (b.thermal?.data_quality !== 'UNAVAILABLE' && b.thermal?.utci_c != null) ? b.thermal.utci_c : -999;
        const diff = valB - valA;
        return sortOrder === 'desc' ? diff : -diff;
      });
  }, [districts, searchTerm, selectedState, sortOrder]);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
      
      {/* Title & Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-slate-900">
            South India 83-District Triage & Monitoring Index
          </h2>
          <p className="text-xs text-slate-500">
            Tamil Nadu (38) • Kerala (14) • Karnataka (31)
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          
          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search district..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="text-xs pl-8 pr-3 py-1.5 rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-1 focus:ring-teal-500 w-36 sm:w-44"
            />
          </div>

          {/* State Filter */}
          <div className="flex items-center gap-1 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedState}
              onChange={(e) => setSelectedState(e.target.value)}
              className="text-xs rounded-lg border border-slate-300 px-2 py-1.5 bg-white text-slate-700 font-medium focus:outline-none focus:ring-1 focus:ring-teal-500"
            >
              <option value="ALL">All States (83)</option>
              <option value="Tamil Nadu">Tamil Nadu (38)</option>
              <option value="Kerala">Kerala (14)</option>
              <option value="Karnataka">Karnataka (31)</option>
            </select>
          </div>

          {/* Sort Order Toggle */}
          <button
            type="button"
            onClick={() => setSortOrder(prev => prev === 'desc' ? 'asc' : 'desc')}
            className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium"
            title="Sort by UTCI thermal stress"
          >
            <ArrowUpDown className="w-3.5 h-3.5" />
            <span>{sortOrder === 'desc' ? 'Highest UTCI' : 'Lowest UTCI'}</span>
          </button>

        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto border border-slate-200 rounded-lg max-h-96">
        <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
          <thead className="bg-slate-50 sticky top-0 z-10 font-bold text-slate-700">
            <tr>
              <th scope="col" className="px-3.5 py-2.5">District</th>
              <th scope="col" className="px-3 py-2.5">State</th>
              <th scope="col" className="px-3 py-2.5 text-right">Air Temp</th>
              <th scope="col" className="px-3 py-2.5 text-right">Rel Humidity</th>
              <th scope="col" className="px-3 py-2.5 text-right">Mean Radiant Temp</th>
              <th scope="col" className="px-3 py-2.5 text-right font-bold text-slate-900">UTCI (°C)</th>
              <th scope="col" className="px-3.5 py-2.5">Category</th>
              <th scope="col" className="px-2 py-2.5 text-center">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {filteredDistricts.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-slate-400">
                  No districts match your search criteria.
                </td>
              </tr>
            ) : (
              filteredDistricts.map((d) => {
                const isSelected = d.id === selectedDistrictId;
                const isUnavailable = d.thermal?.data_quality === 'UNAVAILABLE' || d.thermal?.utci_c == null;
                const catInfo = d.thermal?.category_info;
                const catColor = isUnavailable ? '#94a3b8' : (catInfo?.color || '#0f172a');
                const badgeBg = isUnavailable ? '#f1f5f9' : (catInfo?.badge_bg || '#f1f5f9');
                const badgeText = isUnavailable ? '#475569' : (catInfo?.badge_text || '#334155');
                const badgeBorder = isUnavailable ? '#cbd5e1' : (catInfo?.badge_border || '#cbd5e1');

                return (
                  <tr
                    key={d.id}
                    onClick={() => onSelectDistrict(d.id)}
                    className={`cursor-pointer transition-colors ${
                      isSelected 
                        ? 'bg-teal-50/80 font-medium text-slate-900' 
                        : 'hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <td className="px-3.5 py-2 font-semibold">
                      {d.name}
                    </td>
                    <td className="px-3 py-2 text-slate-500">
                      {d.state}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {d.weather?.temperature_c != null ? `${d.weather.temperature_c.toFixed(1)}°C` : 'N/A'}
                    </td>
                    <td className="px-3 py-2 text-right text-slate-500">
                      {d.weather?.relative_humidity != null ? `${d.weather.relative_humidity.toFixed(0)}%` : 'N/A'}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-slate-600">
                      {d.thermal?.mrt_c != null ? `${d.thermal.mrt_c.toFixed(1)}°C` : 'N/A'}
                    </td>
                    <td className="px-3 py-2 text-right font-bold font-mono text-sm" style={{ color: catColor }}>
                      {isUnavailable ? 'No live data' : `${(d.thermal?.utci_c as number).toFixed(1)}°C`}
                    </td>
                    <td className="px-3.5 py-2">
                      <span
                        className="inline-block px-2 py-0.5 rounded text-[10px] font-bold border"
                        style={{
                          backgroundColor: badgeBg,
                          color: badgeText,
                          borderColor: badgeBorder
                        }}
                      >
                        {isUnavailable ? 'No live data' : (catInfo?.category || 'No live data')}
                      </span>
                    </td>
                    <td className="px-2 py-2 text-center text-slate-400">
                      <ChevronRight className="w-4 h-4 inline-block" />
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

    </div>
  );
};

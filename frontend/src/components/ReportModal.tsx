import React from 'react';
import { X, Printer, Download, FileText, CheckCircle2 } from 'lucide-react';

interface ReportModalProps {
  reportData: any;
  onClose: () => void;
}

export const ReportModal: React.FC<ReportModalProps> = ({ reportData, onClose }) => {
  if (!reportData) return null;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white rounded-xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-xl border border-slate-200">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50 rounded-t-xl">
          <div className="flex items-center gap-2 text-teal-800 font-bold text-sm">
            <FileText className="w-5 h-5 text-teal-600" />
            <span>Official Synthesis Report</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 text-white rounded-lg text-xs font-semibold hover:bg-slate-900 transition-colors shadow-xs"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print / Save PDF</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Printable Report Body */}
        <div className="p-8 overflow-y-auto space-y-6 text-slate-800 text-xs leading-relaxed font-sans" id="printable-report">
          
          {/* Government / Project Header */}
          <div className="border-b-2 border-slate-800 pb-4 flex justify-between items-start">
            <div>
              <h1 className="text-xl font-black tracking-tight text-slate-900 uppercase">
                Ushna Kaappaan Heat Early Warning Report
              </h1>
              <p className="text-xs text-slate-600 font-medium mt-0.5">
                Localized Human Thermal Stress & Early Action Decision Support
              </p>
              <p className="text-[11px] text-slate-500 mt-1">
                Report Identifier: <strong className="font-mono text-slate-700">{reportData.report_id}</strong>
              </p>
            </div>
            <div className="text-right text-xs">
              <span className="inline-block px-2.5 py-1 bg-slate-100 border border-slate-300 rounded font-mono font-bold text-slate-800">
                {reportData.generated_at_ist}
              </span>
              <span className="block text-[10px] text-slate-500 mt-1">Mode: {reportData.mode}</span>
            </div>
          </div>

          {/* District Profile / Summary */}
          {reportData.district_profile ? (
            <div className="space-y-4">
              <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 grid grid-cols-2 gap-4">
                <div>
                  <span className="text-slate-500 block text-[11px]">Assessment Area:</span>
                  <strong className="text-base text-slate-900 font-bold">
                    {reportData.district_profile.name}, {reportData.district_profile.state}
                  </strong>
                </div>
                <div>
                  <span className="text-slate-500 block text-[11px]">Scientific UTCI Thermal Stress:</span>
                  <span className="text-base font-black text-rose-700 font-mono">
                    {reportData.district_profile.thermal?.utci_c?.toFixed(1)}°C
                  </span>
                  <span className="text-slate-600 text-[11px] block font-semibold">
                    ({reportData.district_profile.thermal?.category_info?.category})
                  </span>
                </div>
              </div>

              {/* Physical Variables */}
              <div>
                <h3 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] mb-2">
                  Meteorological Observations
                </h3>
                <div className="grid grid-cols-4 gap-2 text-center">
                  <div className="p-2 border border-slate-200 rounded">
                    <span className="text-slate-400 block text-[10px]">Air Temp:</span>
                    <strong>{reportData.district_profile.weather?.temperature_c?.toFixed(1)}°C</strong>
                  </div>
                  <div className="p-2 border border-slate-200 rounded">
                    <span className="text-slate-400 block text-[10px]">Rel Humidity:</span>
                    <strong>{reportData.district_profile.weather?.relative_humidity?.toFixed(0)}%</strong>
                  </div>
                  <div className="p-2 border border-slate-200 rounded">
                    <span className="text-slate-400 block text-[10px]">Wind (10m):</span>
                    <strong>{reportData.district_profile.weather?.wind_speed_mps?.toFixed(1)} m/s</strong>
                  </div>
                  <div className="p-2 border border-slate-200 rounded">
                    <span className="text-slate-400 block text-[10px]">Mean Radiant:</span>
                    <strong>{reportData.district_profile.thermal?.mrt_c?.toFixed(1)}°C</strong>
                  </div>
                </div>
              </div>

              {/* Recommended Action Directives */}
              <div className="bg-amber-50/60 p-4 rounded-lg border border-amber-200">
                <h3 className="font-bold text-amber-950 uppercase tracking-wider text-[11px] mb-1">
                  Mandatory Public Health Directives
                </h3>
                <p className="text-slate-800 text-xs leading-relaxed">
                  {reportData.recommended_actions}
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
                <h2 className="font-bold text-slate-900 text-sm mb-1">{reportData.report_title}</h2>
                <p className="text-slate-600 text-xs">{reportData.coverage}</p>
              </div>

              {reportData.state_mortality_burdens && (
                <div>
                  <h3 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] mb-2">
                    State-Level Mortality Risk Estimates
                  </h3>
                  <div className="grid grid-cols-3 gap-3">
                    {reportData.state_mortality_burdens.map((s: any) => (
                      <div key={s.state} className="p-3 border border-slate-200 rounded-lg">
                        <strong className="block text-slate-900">{s.state}</strong>
                        <span className="text-xs font-mono font-bold text-teal-800 block mt-1">
                          {s.predicted_rate_display}
                        </span>
                        <span className="text-[10px] text-slate-500 block mt-0.5">{s.risk_context}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Footer Sign-off */}
          <div className="border-t border-slate-200 pt-4 flex items-center justify-between text-[11px] text-slate-500">
            <div>
              <span>System: <strong>Ushna Kaappaan v1.0.0</strong></span>
              <p className="text-[10px] text-slate-400 mt-0.5">
                ECMWF thermofeel • Open-Meteo REST • Ridge Regression ML
              </p>
            </div>
            <div className="text-right">
              <span className="font-semibold text-slate-700">{reportData.signatory || 'State Heat Taskforce'}</span>
              <span className="block text-[10px] text-slate-400">Automated Official Transcript</span>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
};

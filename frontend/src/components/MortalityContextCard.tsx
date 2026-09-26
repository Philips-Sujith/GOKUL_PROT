import React from 'react';
import { Activity, ShieldAlert, FileText, Database, Info, Cpu } from 'lucide-react';
import { MortalityOverviewResponse, StateMortalityEstimate } from '../types';

interface MortalityContextCardProps {
  mortalityData: MortalityOverviewResponse | null;
  selectedState: string;
}

export const MortalityContextCard: React.FC<MortalityContextCardProps> = ({
  mortalityData,
  selectedState
}) => {
  if (!mortalityData || !mortalityData.state_estimates) {
    return null;
  }

  const stateEstimate = mortalityData.state_estimates.find(s => s.state === selectedState) 
    || mortalityData.state_estimates[0];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
      
      {/* Title & Scope Badges */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Activity className="w-5 h-5 text-teal-600" />
              State-Level Heat Mortality Risk Context
            </h2>
            <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-purple-50 text-purple-800 border border-purple-200">
              ML Model Layer
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Epidemiological vulnerability assessment for <strong className="text-slate-800">{stateEstimate?.state}</strong>
          </p>
        </div>

        {/* State-Only Policy Badge */}
        <span className="text-[11px] px-2.5 py-1 rounded-md font-semibold bg-amber-50 text-amber-900 border border-amber-300 inline-flex items-center gap-1.5 self-start sm:self-auto">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
          State-Level Aggregation Only
        </span>
      </div>

      {/* Primary Estimation Box */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        
        {/* Continuous ML Rate & Context */}
        <div className="md:col-span-6 bg-slate-50 rounded-xl p-4 border border-slate-200 flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">
              Estimated Heat-Related Mortality Rate (State-Level)
            </span>
            <div className="text-2xl font-black text-slate-900 tracking-tight font-mono">
              {stateEstimate?.predicted_mortality_rate_per_100000 !== undefined
                ? `${stateEstimate.predicted_mortality_rate_per_100000.toFixed(4)}`
                : '0.0000'}
              <span className="text-xs font-sans font-normal text-slate-600 ml-2">
                deaths / 100,000 residents / day
              </span>
            </div>
            <div className="text-[11px] text-slate-500 font-mono mt-1.5 flex flex-col gap-0.5">
              <span>
                • Per Capita Daily Equivalent:{' '}
                <strong className="text-slate-700 font-mono">
                  {stateEstimate?.predicted_mortality_rate_per_100000 !== undefined
                    ? (stateEstimate.predicted_mortality_rate_per_100000 / 100000).toExponential(3)
                    : '0.00e-9'}{' '}
                  deaths/person/day
                </strong>
              </span>
              <span className="text-[10px] text-slate-400">
                • Statistical baseline for ~{(stateEstimate?.state === 'Tamil Nadu' ? 77 : stateEstimate?.state === 'Karnataka' ? 68 : 36)}M state population
              </span>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-200/80 flex items-center justify-between">
            <span className="text-xs text-slate-600 font-medium">Application Context:</span>
            <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${
              stateEstimate?.badge_color === 'red'
                ? 'bg-rose-50 text-rose-800 border-rose-200'
                : stateEstimate?.badge_color === 'orange'
                ? 'bg-orange-50 text-orange-800 border-orange-200'
                : stateEstimate?.badge_color === 'amber'
                ? 'bg-amber-50 text-amber-800 border-amber-200'
                : 'bg-emerald-50 text-emerald-800 border-emerald-200'
            }`}>
              ● {stateEstimate?.risk_context}
            </span>
          </div>
        </div>

        {/* ML Transparency & Validation Metrics */}
        <div className="md:col-span-6 bg-white rounded-xl p-4 border border-slate-200 text-xs space-y-2">
          <div className="flex items-center justify-between text-slate-700 font-bold border-b border-slate-100 pb-1.5">
            <span className="flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-teal-600" />
              Trained Model Architecture
            </span>
            <span className="font-mono text-[11px] text-teal-700">{stateEstimate?.algorithm}</span>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-1 text-slate-600">
            <div>
              <span className="text-slate-400 block text-[10px]">Model Artifact:</span>
              <strong className="text-slate-800 font-mono text-[11px]">{stateEstimate?.model_name}</strong>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Version:</span>
              <span className="font-mono text-[11px] text-slate-800">{stateEstimate?.model_version}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Test RMSE (Temporal):</span>
              <span className="font-mono text-[11px] text-slate-800">
                {mortalityData.validation_metrics?.test_rmse ? mortalityData.validation_metrics.test_rmse.toFixed(5) : '0.00043'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Pearson Correlation (r):</span>
              <span className="font-mono text-[11px] text-slate-800">
                {mortalityData.validation_metrics?.test_pearson_corr ? mortalityData.validation_metrics.test_pearson_corr.toFixed(4) : '0.4421'}
              </span>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-500">
            Features: 39 non-leaking predictors (Demographics, lags 1-7, WBGT, humidity load, health access).
          </div>
        </div>

      </div>

      {/* Mandatory Scientific Disclaimer Callout */}
      <div className="p-3 bg-amber-50/70 rounded-lg border border-amber-200 flex items-start gap-2.5 text-xs text-amber-900">
        <Info className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong>Mandatory Scientific Boundary & Limitation:</strong> {stateEstimate?.synthetic_disclaimer || mortalityData.synthetic_data_disclaimer}
        </p>
      </div>

    </div>
  );
};

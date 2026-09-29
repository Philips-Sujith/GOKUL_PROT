import React from 'react';
import { Flame, RefreshCw, ShieldAlert, Radio, Sliders, Lock, CheckCircle2 } from 'lucide-react';
import { SystemStatus } from '../types';

interface HeaderProps {
  systemStatus: SystemStatus | null;
  currentMode: 'LIVE' | 'DEMO';
  demoScenario: string;
  onModeChange: (mode: 'LIVE' | 'DEMO', scenario?: string) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  onOpenAdmin: () => void;
  isAdminLoggedIn: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  systemStatus,
  currentMode,
  demoScenario,
  onModeChange,
  onRefresh,
  isRefreshing,
  onOpenAdmin,
  isAdminLoggedIn
}) => {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between py-3 gap-3">
          
          {/* Brand & Subtitle */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-teal-600 text-white flex items-center justify-center shadow-sm">
              <Flame className="w-6 h-6 text-amber-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-slate-900">
                  USHNA KAAPPAAN
                </h1>
                <span className="text-xs px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 border border-teal-200 font-medium">
                  Heat Protector
                </span>
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold uppercase tracking-wider ${
                  currentMode === 'LIVE' 
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-300' 
                    : 'bg-amber-50 text-amber-800 border border-amber-300'
                }`}>
                  {currentMode === 'LIVE' ? '● LIVE MODE' : '⚙ DEMO MODE'}
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">
                From weather conditions to human heat risk • SIH 2026 South India (83 Districts)
              </p>
            </div>
          </div>

          {/* Controls: Mode Switch, Scenarios, Refresh, Admin */}
          <div className="flex flex-wrap items-center gap-2">
            
            {/* Mode Switcher Buttons */}
            <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-100 text-xs font-medium">
              <button
                type="button"
                onClick={() => onModeChange('LIVE')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors ${
                  currentMode === 'LIVE'
                    ? 'bg-white text-teal-800 shadow-sm font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Radio className="w-3.5 h-3.5 text-emerald-600" />
                Live Open-Meteo
              </button>
              <button
                type="button"
                onClick={() => onModeChange('DEMO', demoScenario)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors ${
                  currentMode === 'DEMO'
                    ? 'bg-white text-amber-900 shadow-sm font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Sliders className="w-3.5 h-3.5 text-amber-600" />
                Demo Scenarios
              </button>
            </div>

            {/* Scenario Dropdown (Visible only in DEMO mode) */}
            {currentMode === 'DEMO' && (
              <div className="flex items-center gap-1.5 bg-amber-50 border border-amber-200 px-2 py-1 rounded-lg">
                <span className="text-xs text-amber-800 font-medium">Scenario:</span>
                <select
                  value={demoScenario}
                  onChange={(e) => onModeChange('DEMO', e.target.value)}
                  className="text-xs bg-white border border-amber-300 rounded px-2 py-1 text-slate-800 font-medium focus:outline-none focus:ring-1 focus:ring-teal-500"
                >
                  <option value="NORMAL">1. Normal Baseline (Comfortable)</option>
                  <option value="MODERATE_HEAT">2. Moderate Heat</option>
                  <option value="HIGH_HEAT_STRESS">3. High Heat Stress</option>
                  <option value="SEVERE_HEAT_STRESS">4. Severe Heatwave</option>
                  <option value="EXTREME_HEAT_STRESS">5. Extreme Heat Crisis (UTCI &gt; 46°C)</option>
                </select>
              </div>
            )}

            {/* Refresh Pipeline Button */}
            <button
              type="button"
              onClick={onRefresh}
              disabled={isRefreshing}
              title="Re-run weather fetch & thermofeel thermal computation"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-60 transition-colors shadow-sm"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-slate-600 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>{isRefreshing ? 'Computing...' : 'Refresh Cycle'}</span>
            </button>

            {/* Admin Portal Toggle */}
            <button
              type="button"
              onClick={onOpenAdmin}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors shadow-sm ${
                isAdminLoggedIn
                  ? 'bg-teal-700 text-white hover:bg-teal-800'
                  : 'bg-slate-800 text-white hover:bg-slate-900'
              }`}
            >
              {isAdminLoggedIn ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-teal-200" />
                  <span>Admin Dashboard</span>
                </>
              ) : (
                <>
                  <Lock className="w-3.5 h-3.5 text-slate-300" />
                  <span>Admin Login</span>
                </>
              )}
            </button>
          </div>

        </div>

        {/* Status bar */}
        <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-500 pb-2 border-t border-slate-100 pt-1.5 gap-2">
          <div className="flex items-center gap-4">
            <span>
              <strong className="text-slate-700">Scientific Thermal Engine:</strong> ECMWF thermofeel (Di Napoli et al. 2020 / Brode et al. 2012)
            </span>
            <span className="hidden sm:inline">•</span>
            <span>
              <strong className="text-slate-700">Weather Source:</strong> {systemStatus?.weather_source || systemStatus?.weather_provider || 'Open-Meteo REST API'}
            </span>
          </div>
          <div>
            <span>
              Last updated: <strong className="text-slate-700 font-medium">{systemStatus?.last_pipeline_run_ist || 'Live'}</strong>
            </span>
          </div>
        </div>

      </div>
    </header>
  );
};

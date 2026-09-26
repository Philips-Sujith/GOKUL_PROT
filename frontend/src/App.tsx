import React, { useState, useEffect, useCallback } from 'react';
import { 
  fetchSystemStatus, 
  updateSystemMode, 
  triggerPipelineRefresh, 
  fetchDistricts, 
  fetchDistrictDetails, 
  fetchPopulationProfiles, 
  fetchMortalityOverview, 
  fetchAlerts 
} from './services/api';
import { 
  DistrictSummary, 
  PopulationProfile, 
  MortalityOverviewResponse, 
  AlertItem, 
  TelegramDeliveryItem, 
  SystemStatus 
} from './types';

import { Header } from './components/Header';
import { GisMap } from './components/GisMap';
import { SelectedDistrictCard } from './components/SelectedDistrictCard';
import { PopulationProfilesCard } from './components/PopulationProfilesCard';
import { MortalityContextCard } from './components/MortalityContextCard';
import { DistrictsTable } from './components/DistrictsTable';
import { AdminPortal } from './components/AdminPortal';
import { ReportModal } from './components/ReportModal';

export const App: React.FC = () => {
  // Navigation tab: 'public' | 'admin'
  const [activeTab, setActiveTab] = useState<'public' | 'admin'>('public');

  // Application Mode & Scenarios
  const [currentMode, setCurrentMode] = useState<'LIVE' | 'DEMO'>('LIVE');
  const [demoScenario, setDemoScenario] = useState<string>('HIGH_HEAT_STRESS');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Core Data
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [districts, setDistricts] = useState<DistrictSummary[]>([]);
  const [selectedDistrictId, setSelectedDistrictId] = useState<string>('TN-03'); // Default Chennai
  const [selectedDistrictDetail, setSelectedDistrictDetail] = useState<DistrictSummary | null>(null);
  const [historyTrend, setHistoryTrend] = useState<any[]>([]);
  const [profiles, setProfiles] = useState<PopulationProfile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<string>('general_public');
  const [mortalityData, setMortalityData] = useState<MortalityOverviewResponse | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [telegramDeliveries, setTelegramDeliveries] = useState<TelegramDeliveryItem[]>([]);

  // Admin state
  const [isAdminLoggedIn, setIsAdminLoggedIn] = useState(false);
  const [reportModalData, setReportModalData] = useState<any | null>(null);

  // Initial load & data fetching
  const loadAllData = useCallback(async () => {
    try {
      const [statusRes, distRes, profRes, mortRes, alertRes] = await Promise.all([
        fetchSystemStatus(),
        fetchDistricts(),
        fetchPopulationProfiles(),
        fetchMortalityOverview(),
        fetchAlerts()
      ]);

      setSystemStatus(statusRes);
      setCurrentMode(statusRes.mode as 'LIVE' | 'DEMO');
      if (statusRes.demo_scenario) setDemoScenario(statusRes.demo_scenario);
      
      setDistricts(distRes.districts);
      setProfiles(profRes.profiles);
      setMortalityData(mortRes);
      setAlerts(alertRes.alerts);
      setTelegramDeliveries(alertRes.telegram_deliveries);

      // Select initial district if not set
      if (distRes.districts.length > 0) {
        const targetId = selectedDistrictId || distRes.districts[0].id;
        const detailRes = await fetchDistrictDetails(targetId);
        setSelectedDistrictDetail(detailRes.district);
        setHistoryTrend(detailRes.history_trend || []);
      }
    } catch (err) {
      console.error('Error loading initial application data:', err);
    }
  }, [selectedDistrictId]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Handle District Selection
  const handleSelectDistrict = async (districtId: string) => {
    setSelectedDistrictId(districtId);
    try {
      const res = await fetchDistrictDetails(districtId);
      setSelectedDistrictDetail(res.district);
      setHistoryTrend(res.history_trend || []);
    } catch (err) {
      console.error('Error loading district details:', err);
    }
  };

  // Handle Mode & Scenario Switch
  const handleModeChange = async (mode: 'LIVE' | 'DEMO', scenario?: string) => {
    setIsRefreshing(true);
    try {
      await updateSystemMode(mode, scenario || demoScenario);
      setCurrentMode(mode);
      if (scenario) setDemoScenario(scenario);
      await loadAllData();
    } catch (err) {
      console.error('Failed to change mode:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Handle Manual Pipeline Refresh
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await triggerPipelineRefresh();
      await loadAllData();
    } catch (err) {
      console.error('Failed to refresh pipeline:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col text-slate-900">
      
      {/* Top Header */}
      <Header
        systemStatus={systemStatus}
        currentMode={currentMode}
        demoScenario={demoScenario}
        onModeChange={handleModeChange}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        onOpenAdmin={() => setActiveTab(prev => prev === 'admin' ? 'public' : 'admin')}
        isAdminLoggedIn={isAdminLoggedIn}
      />

      {/* Main Container */}
      <main className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 space-y-6">
        
        {/* Navigation Tabs */}
        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab('public')}
              className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors ${
                activeTab === 'public'
                  ? 'bg-teal-700 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              Public Early Warning Portal
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('admin')}
              className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 ${
                activeTab === 'admin'
                  ? 'bg-slate-800 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <span>Admin Taskforce Dashboard</span>
              {alerts.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full bg-rose-500 text-white text-[10px] font-mono">
                  {alerts.length}
                </span>
              )}
            </button>
          </div>

          <span className="text-xs text-slate-500 hidden sm:inline">
            South India Geographic Coverage: <strong>83 Districts</strong>
          </span>
        </div>

        {/* Tab View 1: Public Portal */}
        {activeTab === 'public' && (
          <div className="space-y-6">
            
            {/* Top Grid: GIS Map (Left 7) + Selected District Card (Right 5) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              <div className="lg:col-span-7">
                <GisMap
                  districts={districts}
                  selectedDistrictId={selectedDistrictId}
                  onSelectDistrict={handleSelectDistrict}
                  mode={currentMode}
                />
              </div>

              <div className="lg:col-span-5">
                <SelectedDistrictCard
                  district={selectedDistrictDetail}
                  historyTrend={historyTrend}
                />
              </div>
            </div>

            {/* Population / Occupation Health Advisory Layer */}
            <PopulationProfilesCard
              profiles={profiles}
              selectedProfileId={selectedProfileId}
              onSelectProfile={setSelectedProfileId}
              district={selectedDistrictDetail}
            />

            {/* State-Level Mortality Risk ML Context */}
            <MortalityContextCard
              mortalityData={mortalityData}
              selectedState={selectedDistrictDetail?.state || 'Tamil Nadu'}
            />

            {/* 83-District Triage Table */}
            <DistrictsTable
              districts={districts}
              selectedDistrictId={selectedDistrictId}
              onSelectDistrict={handleSelectDistrict}
            />

          </div>
        )}

        {/* Tab View 2: Admin Dashboard */}
        {activeTab === 'admin' && (
          <AdminPortal
            districts={districts}
            alerts={alerts}
            telegramDeliveries={telegramDeliveries}
            systemStatus={systemStatus}
            isAdminLoggedIn={isAdminLoggedIn}
            onLoginSuccess={() => setIsAdminLoggedIn(true)}
            onLogout={() => setIsAdminLoggedIn(false)}
            onOpenReport={setReportModalData}
            onRefreshData={loadAllData}
          />
        )}

      </main>

      {/* Synthesis Report Modal */}
      {reportModalData && (
        <ReportModal
          reportData={reportModalData}
          onClose={() => setReportModalData(null)}
        />
      )}

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 mt-12 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-3 text-center md:text-left">
          <div>
            <strong className="text-slate-800">Ushna Kaappaan (Heat Protector)</strong> — Localized Heat Stress & Early Warning System
            <p className="text-[11px] text-slate-400 mt-0.5">
              ECMWF thermofeel • Open-Meteo REST • Ridge Regression ML • Leaflet GIS • Telegram Integration
            </p>
          </div>
          <div className="text-xs text-slate-400">
            Smart India Hackathon (SIH 2026) Prototype
          </div>
        </div>
      </footer>

    </div>
  );
};
export default App;

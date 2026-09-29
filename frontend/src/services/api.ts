import {
  DistrictSummary,
  PopulationProfile,
  MortalityOverviewResponse,
  AlertItem,
  TelegramDeliveryItem,
  SystemStatus
} from '../types';

const envApiUrl = import.meta.env.VITE_API_URL;
const BASE_URL = envApiUrl 
  ? (envApiUrl.endsWith('/api') ? envApiUrl : `${envApiUrl.replace(/\/+$/, '')}/api`)
  : '/api';

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(`${BASE_URL}/system/status`);
  if (!res.ok) throw new Error('Failed to fetch system status');
  return res.json();
}

export async function updateSystemMode(mode: 'LIVE' | 'DEMO', demoScenario?: string): Promise<{ message: string; mode: string; demo_scenario?: string }> {
  const res = await fetch(`${BASE_URL}/system/mode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode, demo_scenario: demoScenario })
  });
  if (!res.ok) throw new Error('Failed to update system mode');
  return res.json();
}

export async function triggerPipelineRefresh(): Promise<any> {
  const res = await fetch(`${BASE_URL}/system/refresh`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to trigger pipeline refresh');
  return res.json();
}

export async function fetchDistricts(state?: string): Promise<{ total_districts: number; mode: string; districts: DistrictSummary[] }> {
  const url = state ? `${BASE_URL}/districts?state=${encodeURIComponent(state)}` : `${BASE_URL}/districts`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch districts');
  return res.json();
}

export async function fetchDistrictDetails(districtId: string): Promise<{ district: DistrictSummary; history_trend: any[]; mode: string }> {
  const res = await fetch(`${BASE_URL}/districts/${districtId}`);
  if (!res.ok) throw new Error(`Failed to fetch district ${districtId}`);
  return res.json();
}

export async function fetchThermalOverview(): Promise<any> {
  const res = await fetch(`${BASE_URL}/thermal/latest`);
  if (!res.ok) throw new Error('Failed to fetch thermal overview');
  return res.json();
}

export async function fetchPopulationProfiles(): Promise<{ profiles: PopulationProfile[] }> {
  const res = await fetch(`${BASE_URL}/population-profiles`);
  if (!res.ok) throw new Error('Failed to fetch population profiles');
  return res.json();
}

export async function fetchHealthImpact(districtId: string, profileId: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/health-impact/${districtId}?profile=${profileId}`);
  if (!res.ok) throw new Error(`Failed to fetch health advisory for ${districtId}`);
  return res.json();
}

export async function fetchMortalityOverview(): Promise<MortalityOverviewResponse> {
  const res = await fetch(`${BASE_URL}/mortality/overview`);
  if (!res.ok) throw new Error('Failed to fetch mortality overview');
  return res.json();
}

export async function fetchAlerts(): Promise<{ mode: string; total_active_alerts: number; alerts: AlertItem[]; telegram_deliveries: TelegramDeliveryItem[] }> {
  const res = await fetch(`${BASE_URL}/alerts`);
  if (!res.ok) throw new Error('Failed to fetch alerts');
  return res.json();
}

export async function adminLogin(username: string, password: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/admin/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Login failed');
  }
  return res.json();
}

export async function sendManualEscalation(data: {
  district_id: string;
  operational_severity: string;
  custom_advisory: string;
  target_roles: string[];
}): Promise<any> {
  const res = await fetch(`${BASE_URL}/admin/escalations/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error('Failed to dispatch escalation');
  return res.json();
}

export async function generateReport(districtId?: string, state?: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/admin/reports/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ district_id: districtId, state })
  });
  if (!res.ok) throw new Error('Failed to generate report');
  return res.json();
}

export async function fetchDistrictForecast(districtId: string): Promise<{ mode: string; forecast: any }> {
  const res = await fetch(`${BASE_URL}/forecast/district/${encodeURIComponent(districtId)}`);
  if (!res.ok) throw new Error(`Failed to fetch 3-day forecast for ${districtId}`);
  return res.json();
}

export async function fetchAllForecasts(state?: string): Promise<{ total_districts: number; mode: string; forecasts: any[] }> {
  const url = state ? `${BASE_URL}/forecast/all?state=${encodeURIComponent(state)}` : `${BASE_URL}/forecast/all`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch 3-day district forecasts');
  return res.json();
}

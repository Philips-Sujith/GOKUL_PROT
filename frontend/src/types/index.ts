export interface UTCICategoryInfo {
  category: string;
  min_utci: number;
  max_utci: number;
  severity_rank: number;
  color: string;
  badge_bg: string;
  badge_text: string;
  badge_border: string;
  description: string;
}

export interface WeatherData {
  temperature_c: number;
  relative_humidity: number;
  wind_speed_mps: number;
  wind_direction_deg?: number;
  surface_pressure_hpa?: number;
  shortwave_radiation_wm2?: number;
  direct_radiation_wm2?: number;
  diffuse_radiation_wm2?: number;
  data_quality?: string;
}

export interface ThermalData {
  mrt_c: number;
  utci_c: number;
  category_info: UTCICategoryInfo;
  data_quality?: string;
  solar_zenith_angle_deg?: number;
  cos_zenith_angle?: number;
  vapour_pressure_hpa?: number;
}

export interface DistrictSummary {
  id: string;
  name: string;
  state: string;
  latitude: number;
  longitude: number;
  elevation?: number;
  weather: WeatherData;
  thermal: ThermalData;
  timestamp_ist: string;
  mode: string;
  scenario?: string;
}

export interface PopulationProfile {
  id: string;
  name: string;
  icon: string;
  description: string;
  vulnerability_weight: string;
  advisories_by_category: Record<string, {
    summary: string;
    precautions: string[];
    symptoms_watch: string[];
  }>;
}

export interface StateMortalityEstimate {
  state: string;
  timestamp_utc: string;
  timestamp_ist: string;
  predicted_mortality_rate_per_100000: number;
  predicted_rate_display: string;
  risk_context: string;
  badge_color: string;
  model_name: string;
  model_version: string;
  algorithm: string;
  data_type: string;
  spatial_scope: string;
  mode: string;
  validation_summary?: {
    test_rmse?: number;
    test_mae?: number;
    test_r2?: number;
    test_pearson_corr?: number;
    train_rmse?: number;
  };
  synthetic_disclaimer: string;
}

export interface MortalityOverviewResponse {
  mode: string;
  spatial_resolution: string;
  district_prediction_policy: string;
  model_metadata: Record<string, any>;
  validation_metrics: Record<string, any>;
  state_estimates: StateMortalityEstimate[];
  synthetic_data_disclaimer: string;
}

export interface AlertItem {
  id: number;
  alert_uid: string;
  district_id: string;
  district_name: string;
  state: string;
  utci_c: number;
  utci_category: string;
  operational_severity: string;
  recipient_roles: string[];
  advisory_text: string;
  status: string;
  mode: string;
  created_at: string;
}

export interface TelegramDeliveryItem {
  id: number;
  alert_id?: number;
  recipient_role: string;
  chat_id: string;
  message_body: string;
  transport_mode: string;
  delivery_status: string;
  error_message?: string;
  sent_at: string;
}

export interface SystemStatus {
  app_name: string;
  full_title: string;
  tagline: string;
  version: string;
  mode: string;
  demo_scenario?: string;
  available_demo_scenarios: string[];
  districts_count: number;
  active_alerts_count: number;
  last_pipeline_run_ist: string;
  pipeline_status: string;
  weather_provider: string;
  thermal_engine: string;
  mortality_model: {
    status: string;
    version: string;
    data_type: string;
  };
  telegram_integration: {
    is_configured: boolean;
    transport_mode: string;
    bot_status: string;
  };
}

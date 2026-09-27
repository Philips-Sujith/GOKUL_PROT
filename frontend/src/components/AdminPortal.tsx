import React, { useState } from 'react';
import { 
  ShieldAlert, 
  Send, 
  FileText, 
  Lock, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Radio, 
  LogOut, 
  UserCheck, 
  BellRing,
  Cpu,
  Copy,
  Check,
  Eye,
  Info,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { DistrictSummary, AlertItem, TelegramDeliveryItem, SystemStatus } from '../types';
import { adminLogin, sendManualEscalation, generateReport } from '../services/api';
import { AdminForecastTable } from './AdminForecastTable';

interface AdminPortalProps {
  districts: DistrictSummary[];
  alerts: AlertItem[];
  telegramDeliveries: TelegramDeliveryItem[];
  systemStatus: SystemStatus | null;
  isAdminLoggedIn: boolean;
  onLoginSuccess: () => void;
  onLogout: () => void;
  onOpenReport: (reportData: any) => void;
  onRefreshData: () => void;
}

export const AdminPortal: React.FC<AdminPortalProps> = ({
  districts,
  alerts,
  telegramDeliveries,
  systemStatus,
  isAdminLoggedIn,
  onLoginSuccess,
  onLogout,
  onOpenReport,
  onRefreshData
}) => {
  // Login form state
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin@ushna2026');
  const [loginError, setLoginError] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  // Manual Escalation form state
  const [selectedDistrictId, setSelectedDistrictId] = useState(districts[0]?.id || 'TN-03');
  const [escalationSeverity, setEscalationSeverity] = useState('SEVERE');
  const [customAdvisory, setCustomAdvisory] = useState(
    'SUGGESTED PRECAUTIONARY ACTION: Reschedule heavy open-ground physical work to cooler morning hours (before 11:00 AM). Ensure shaded rest spaces, cool drinking water, and oral rehydration salts (ORS) are accessible across active work sites.'
  );
  const [targetRoles, setTargetRoles] = useState<string[]>([
    'Municipality Authorities', 
    'Public Health Centres', 
    'Worker Union Leaders'
  ]);
  const [isEscalating, setIsEscalating] = useState(false);
  const [escalationMessage, setEscalationMessage] = useState('');
  const [copiedId, setCopiedId] = useState<number | string | null>(null);

  // Selected delivery for full modal view
  const [expandedDelivery, setExpandedDelivery] = useState<TelegramDeliveryItem | null>(null);

  // Report generation state
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);

  // Priority districts triage expansion state
  const [showAllPriorityDistricts, setShowAllPriorityDistricts] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoggingIn(true);
    setLoginError('');
    try {
      await adminLogin(username, password);
      onLoginSuccess();
    } catch (err: any) {
      setLoginError(err.message || 'Invalid credentials');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleEscalate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsEscalating(true);
    setEscalationMessage('');
    try {
      const res = await sendManualEscalation({
        district_id: selectedDistrictId,
        operational_severity: escalationSeverity,
        custom_advisory: customAdvisory,
        target_roles: targetRoles
      });
      setEscalationMessage(`Dispatched escalation to ${res.result?.deliveries?.length || 0} recipient channels!`);
      onRefreshData();
    } catch (err: any) {
      setEscalationMessage(`Failed: ${err.message}`);
    } finally {
      setIsEscalating(false);
    }
  };

  const handleGenerateReport = async (districtId?: string) => {
    setIsGeneratingReport(true);
    try {
      const res = await generateReport(districtId);
      onOpenReport(res);
    } catch (err) {
      alert('Failed to generate report');
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const toggleRole = (role: string) => {
    setTargetRoles(prev => 
      prev.includes(role) ? prev.filter(r => r !== role) : [...prev, role]
    );
  };

  const copyToClipboard = (text: string, id: number | string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Selected district info for live preview
  const selectedDistrict = districts.find(d => d.id === selectedDistrictId) || districts[0];
  const livePreviewBody = `🔥 *USHNA KAAPPAAN — HEAT EARLY WARNING*
${systemStatus?.telegram_integration.transport_mode === 'REAL' ? '🔴 [LIVE SYSTEM ALERT]' : '🟡 [MOCK / TEST SCENARIO]'}

📍 *District:* ${selectedDistrict?.name || 'Chennai'}, ${selectedDistrict?.state || 'Tamil Nadu'}
🌡 *Thermal Stress (UTCI):* \`${(selectedDistrict?.thermal?.utci_c || 38.0).toFixed(1)}°C\`
⚠️ *Category:* ${selectedDistrict?.thermal?.category_info?.category || 'Very strong heat stress'}
🚨 *Operational Severity:* ${escalationSeverity}
👥 *Target Roles:* ${targetRoles.join(', ')}
🕒 *Time:* ${new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })} IST

📋 *Suggested Precautionary Actions:*
${customAdvisory}

⚠️ _Note: Advisory generated for decision support. Official directives are issued by competent administrative authorities._
ℹ️ _Generated by Ushna Kaappaan Localized Heat Early Warning Platform._`;

  // High-risk districts (UTCI >= 38.0°C) sorted deterministically by highest UTCI first
  const highRiskDistricts = [...districts]
    .filter(d => (d.thermal?.utci_c || 0) >= 38.0)
    .sort((a, b) => (b.thermal?.utci_c || 0) - (a.thermal?.utci_c || 0));

  if (!isAdminLoggedIn) {
    return (
      <div className="max-w-md mx-auto my-12 bg-white rounded-xl border border-slate-200 p-8 shadow-sm">
        <div className="text-center mb-6">
          <div className="w-12 h-12 rounded-full bg-slate-900 text-white flex items-center justify-center mx-auto mb-3 shadow-xs">
            <Lock className="w-6 h-6 text-teal-400" />
          </div>
          <h2 className="text-lg font-bold text-slate-900">Admin Portal Authentication</h2>
          <p className="text-xs text-slate-500 mt-1">
            Ushna Kaappaan State Control Dashboard Access
          </p>
        </div>

        {loginError && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center gap-2">
            <XCircle className="w-4 h-4 shrink-0" />
            <span>{loginError}</span>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-teal-500 font-medium"
              required
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-teal-500 font-medium"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoggingIn}
            className="w-full py-2.5 bg-teal-700 text-white font-bold rounded-lg hover:bg-teal-800 disabled:opacity-60 transition-colors shadow-xs"
          >
            {isLoggingIn ? 'Authenticating...' : 'Sign In to Admin Portal'}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-slate-100 text-[11px] text-slate-500 text-center">
          Default Prototype Credentials: <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-800">admin</code> / <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-800">admin@ushna2026</code>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* Top Admin Banner */}
      <div className="bg-slate-900 text-white rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <h2 className="text-lg font-bold">State Disaster Management & Heat Taskforce Console</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Operational triage, manual escalation directives, early-warning Telegram broadcasts, and syntheses.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => handleGenerateReport()}
            disabled={isGeneratingReport}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Generate Synthesis Report</span>
          </button>
          
          <button
            type="button"
            onClick={onLogout}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Logout</span>
          </button>
        </div>
      </div>

      {/* Feature 2: 3-Day District Heat-Stress Forecast Table */}
      <AdminForecastTable 
        onSelectDistrictForEscalation={(distId) => {
          setSelectedDistrictId(distId);
        }}
      />

      {/* Admin Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left 7 Columns: High Risk Triage & Telegram Delivery Audit */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* High-Risk Districts Triage */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600" />
                High Thermal Stress District Triage (UTCI &ge; 38°C)
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-rose-50 text-rose-700 border border-rose-200">
                  {highRiskDistricts.length} Priority Units
                </span>
                {highRiskDistricts.length > 6 && (
                  <button
                    type="button"
                    onClick={() => setShowAllPriorityDistricts(!showAllPriorityDistricts)}
                    className="text-xs font-semibold text-teal-700 hover:text-teal-900 hover:bg-teal-50 px-2 py-0.5 rounded transition-colors flex items-center gap-1 border border-teal-200"
                  >
                    {showAllPriorityDistricts ? (
                      <>
                        <span>Show top 6</span>
                        <ChevronUp className="w-3.5 h-3.5" />
                      </>
                    ) : (
                      <>
                        <span>View all</span>
                        <ChevronDown className="w-3.5 h-3.5" />
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {highRiskDistricts.length === 0 ? (
              <div className="p-4 bg-emerald-50 text-emerald-800 text-xs rounded-lg border border-emerald-200 text-center font-medium">
                ✓ No districts currently exceed the critical 38.0°C thermal stress threshold.
              </div>
            ) : (
              <div className="space-y-3">
                <div className={`grid grid-cols-1 sm:grid-cols-2 gap-2.5 ${showAllPriorityDistricts ? 'max-h-80 overflow-y-auto pr-1' : ''}`}>
                  {(showAllPriorityDistricts ? highRiskDistricts : highRiskDistricts.slice(0, 6)).map(d => (
                    <div key={d.id} className="bg-slate-50 p-3 rounded-lg border border-slate-200 flex items-center justify-between hover:bg-slate-100/80 transition-colors">
                      <div>
                        <strong className="text-slate-900 text-xs block">{d.name}</strong>
                        <span className="text-[10px] text-slate-500">{d.state} • Air: {d.weather?.temperature_c?.toFixed(1)}°C</span>
                      </div>
                      <div className="text-right">
                        <span className="text-sm font-black font-mono text-rose-700 block">
                          {d.thermal?.utci_c?.toFixed(1)}°C
                        </span>
                        <span className="text-[9px] font-bold text-rose-800 uppercase">
                          {d.thermal?.category_info?.category}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                {highRiskDistricts.length > 6 && (
                  <div className="pt-1 text-center">
                    <button
                      type="button"
                      onClick={() => setShowAllPriorityDistricts(!showAllPriorityDistricts)}
                      className="text-xs font-semibold text-teal-700 hover:text-teal-900 bg-teal-50/80 hover:bg-teal-100/80 px-3 py-1.5 rounded-lg transition-colors inline-flex items-center gap-1.5 border border-teal-200"
                    >
                      {showAllPriorityDistricts ? (
                        <>
                          <ChevronUp className="w-3.5 h-3.5" />
                          <span>Collapse to top 6 priority districts</span>
                        </>
                      ) : (
                        <>
                          <ChevronDown className="w-3.5 h-3.5" />
                          <span>View all {highRiskDistricts.length} priority districts (sorted by highest UTCI)</span>
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Telegram Broadcast Delivery Log */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Send className="w-4 h-4 text-blue-600" />
                  Telegram Early Warning Delivery Log
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Complete unclipped messages & transmission audit trail
                </p>
              </div>

              <span className={`text-[10px] px-2.5 py-1 rounded font-bold uppercase tracking-wider border ${
                systemStatus?.telegram_integration.is_configured
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                  : 'bg-amber-50 text-amber-800 border-amber-300'
              }`}>
                {systemStatus?.telegram_integration.is_configured ? 'REAL BOT API' : 'MOCK / TEST MODE'}
              </span>
            </div>

            <div className="overflow-y-auto max-h-80 border border-slate-200 rounded-lg text-xs">
              {telegramDeliveries.length === 0 ? (
                <div className="p-4 text-center text-slate-400">
                  No telegram notifications recorded in this cycle.
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {telegramDeliveries.map(del => {
                    const isMock = del.transport_mode === 'MOCK' || del.delivery_status.includes('MOCK') || del.delivery_status === 'SIMULATED';
                    return (
                      <div key={del.id} className="p-3 hover:bg-slate-50/80 transition-colors space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                            <BellRing className="w-3.5 h-3.5 text-teal-600" />
                            {del.recipient_role}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold border ${
                              isMock
                                ? 'bg-amber-50 text-amber-900 border-amber-300'
                                : del.delivery_status === 'SENT'
                                ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                                : 'bg-rose-50 text-rose-800 border-rose-300'
                            }`}>
                              {isMock ? 'MOCK / TEST — NOT ACTUALLY SENT' : del.delivery_status}
                            </span>
                            <button
                              type="button"
                              onClick={() => copyToClipboard(del.message_body, del.id)}
                              className="p-1 text-slate-500 hover:text-slate-900 rounded hover:bg-slate-200 transition-colors"
                              title="Copy Telegram Message"
                            >
                              {copiedId === del.id ? (
                                <Check className="w-3.5 h-3.5 text-emerald-600" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>
                        </div>

                        {/* Full unclipped message with preserved line breaks */}
                        <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-[11px] font-mono whitespace-pre-wrap text-slate-700 leading-relaxed overflow-x-auto">
                          {del.message_body}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

        </div>

        {/* Right 5 Columns: Manual Escalation Broadcast Form & Live Preview */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
          
          <div className="border-b border-slate-100 pb-2.5">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              Manual Escalation & Precautionary Broadcast
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Review and dispatch early-warning advisories to targeted administrative channels.
            </p>
          </div>

          {escalationMessage && (
            <div className="p-3 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-semibold flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{escalationMessage}</span>
            </div>
          )}

          <form onSubmit={handleEscalate} className="space-y-3.5 text-xs">
            
            {/* Target District */}
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Target District</label>
              <select
                value={selectedDistrictId}
                onChange={(e) => setSelectedDistrictId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white font-medium focus:outline-none focus:ring-1 focus:ring-teal-500"
              >
                {districts.map(d => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.state}) — Current UTCI: {d.thermal?.utci_c?.toFixed(1)}°C
                  </option>
                ))}
              </select>
            </div>

            {/* Operational Severity Override */}
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Escalation Severity Level</label>
              <select
                value={escalationSeverity}
                onChange={(e) => setEscalationSeverity(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white font-bold focus:outline-none focus:ring-1 focus:ring-teal-500 text-rose-800"
              >
                <option value="EXTREME">EXTREME (All civic agencies, hospitals, unions & public)</option>
                <option value="SEVERE">SEVERE (Municipalities, health centres & unions)</option>
                <option value="HIGH">HIGH (Municipalities & health centres)</option>
              </select>
            </div>

            {/* Target Role Channels Checkboxes */}
            <div>
              <label className="block font-semibold text-slate-700 mb-1.5">Dispatch Recipient Roles</label>
              <div className="space-y-1.5">
                {[
                  'Municipality Authorities',
                  'Public Health Centres',
                  'Worker Union Leaders',
                  'General Public Channels'
                ].map((role) => (
                  <label key={role} className="flex items-center gap-2 cursor-pointer text-slate-700 font-medium">
                    <input
                      type="checkbox"
                      checked={targetRoles.includes(role)}
                      onChange={() => toggleRole(role)}
                      className="rounded text-teal-600 focus:ring-teal-500 h-3.5 w-3.5"
                    />
                    <span>{role}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Custom Advisory / Precaution Wording */}
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Suggested Precautionary Action Wording
              </label>
              <textarea
                rows={3}
                value={customAdvisory}
                onChange={(e) => setCustomAdvisory(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-teal-500 text-xs font-medium leading-relaxed"
                required
              />
            </div>

            {/* Live Unclipped Telegram Message Preview */}
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-700 flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5 text-teal-600" />
                  Live Telegram Message Preview (Before Dispatch)
                </span>
                <button
                  type="button"
                  onClick={() => copyToClipboard(livePreviewBody, 'preview')}
                  className="flex items-center gap-1 text-[10px] text-teal-700 hover:text-teal-900 font-semibold"
                >
                  {copiedId === 'preview' ? (
                    <>
                      <Check className="w-3 h-3 text-emerald-600" />
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      <span>Copy Preview</span>
                    </>
                  )}
                </button>
              </div>

              <div className="bg-white p-2.5 rounded border border-slate-200 text-[10px] font-mono whitespace-pre-wrap text-slate-800 max-h-40 overflow-y-auto leading-relaxed">
                {livePreviewBody}
              </div>

              <div className="text-[10px] text-amber-800 bg-amber-50/80 p-1.5 rounded border border-amber-200 flex items-center gap-1">
                <Info className="w-3 h-3 text-amber-600 shrink-0" />
                <span>
                  {systemStatus?.telegram_integration.is_configured 
                    ? 'Transmitting via live configured Telegram Bot API.' 
                    : 'Mock transport active: simulated locally with identical message payload.'}
                </span>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isEscalating || targetRoles.length === 0}
              className="w-full py-2.5 bg-teal-700 text-white font-bold rounded-lg hover:bg-teal-800 disabled:opacity-60 transition-colors shadow-xs flex items-center justify-center gap-2"
            >
              <Send className="w-4 h-4" />
              <span>{isEscalating ? 'Broadcasting...' : 'Broadcast Precautionary Escalation'}</span>
            </button>

          </form>

        </div>

      </div>

    </div>
  );
};

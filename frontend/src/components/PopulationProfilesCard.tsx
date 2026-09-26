import React from 'react';
import { 
  Users, 
  HardHat, 
  Tractor, 
  Hammer, 
  Truck, 
  Laptop, 
  GraduationCap, 
  BookOpen, 
  HeartPulse, 
  ShieldCheck, 
  AlertCircle,
  Info
} from 'lucide-react';
import { PopulationProfile, DistrictSummary } from '../types';

interface PopulationProfilesCardProps {
  profiles: PopulationProfile[];
  selectedProfileId: string;
  onSelectProfile: (profileId: string) => void;
  district: DistrictSummary | null;
}

const ICON_MAP: Record<string, React.ReactNode> = {
  Users: <Users className="w-4 h-4" />,
  HardHat: <HardHat className="w-4 h-4" />,
  Tractor: <Tractor className="w-4 h-4" />,
  Hammer: <Hammer className="w-4 h-4" />,
  Truck: <Truck className="w-4 h-4" />,
  Laptop: <Laptop className="w-4 h-4" />,
  GraduationCap: <GraduationCap className="w-4 h-4" />,
  BookOpen: <BookOpen className="w-4 h-4" />,
  HeartPulse: <HeartPulse className="w-4 h-4" />
};

export const PopulationProfilesCard: React.FC<PopulationProfilesCardProps> = ({
  profiles,
  selectedProfileId,
  onSelectProfile,
  district
}) => {
  const selectedProfile = profiles.find(p => p.id === selectedProfileId) || profiles[0];
  const utciCatName = district?.thermal?.category_info?.category || 'No thermal stress';
  const advisoryData = selectedProfile?.advisories_by_category?.[utciCatName] || {
    summary: 'Standard general guidance for current weather conditions.',
    precautions: ['Stay adequately hydrated throughout the day.'],
    symptoms_watch: ['None']
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
      
      {/* Header with Title and Scientific Boundary Reminder */}
      <div>
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Users className="w-5 h-5 text-teal-600" />
            Population & Occupational Health Advisory
          </h2>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-teal-50 text-teal-800 border border-teal-200">
            9 Tailored Profiles
          </span>
        </div>

        {/* Essential Scientific Boundary Callout */}
        <div className="mt-2.5 p-2.5 bg-blue-50/70 rounded-lg border border-blue-200 flex items-start gap-2 text-xs text-blue-900">
          <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
          <p className="leading-snug">
            <strong>Scientific Note:</strong> Selecting an occupation profile changes the <em>exposure context, actionable precautions, and symptom surveillance</em>. It does <strong>NOT</strong> change the physical weather, Mean Radiant Temperature, or scientific UTCI calculation.
          </p>
        </div>
      </div>

      {/* Profile Selector Tabs */}
      <div className="grid grid-cols-3 sm:grid-cols-5 md:grid-cols-9 gap-1.5 pt-1">
        {profiles.map((prof) => {
          const isSelected = prof.id === selectedProfileId;
          const iconNode = ICON_MAP[prof.icon] || <Users className="w-4 h-4" />;

          return (
            <button
              key={prof.id}
              type="button"
              onClick={() => onSelectProfile(prof.id)}
              className={`flex flex-col items-center justify-center p-2 rounded-lg border text-center transition-all ${
                isSelected
                  ? 'bg-teal-50 border-teal-500 text-teal-900 font-semibold shadow-xs ring-1 ring-teal-500'
                  : 'bg-slate-50/70 border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              <span className={`mb-1 ${isSelected ? 'text-teal-700' : 'text-slate-500'}`}>
                {iconNode}
              </span>
              <span className="text-[11px] leading-tight line-clamp-1">
                {prof.name}
              </span>
            </button>
          );
        })}
      </div>

      {/* Selected Profile Details & Tailored Advisory */}
      {selectedProfile && (
        <div className="bg-slate-50/80 rounded-xl p-4 border border-slate-200 space-y-3">
          
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 border-b border-slate-200/80 pb-2.5">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-slate-900 text-sm">{selectedProfile.name}</h3>
                <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-slate-200 text-slate-800">
                  Vulnerability: {selectedProfile.vulnerability_weight}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">{selectedProfile.description}</p>
            </div>
            
            <div className="text-xs text-slate-600 font-medium">
              Category: <strong className="text-slate-900">{utciCatName}</strong>
            </div>
          </div>

          {/* Advisory Summary Banner */}
          <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-xs">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-1 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
              Exposure Advisory & Operational Directive
            </h4>
            <p className="text-xs text-slate-700 leading-relaxed font-medium">
              {advisoryData.summary}
            </p>
          </div>

          {/* Actionable Precautions & Symptoms Watch */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3 pt-1">
            
            {/* Precautions List */}
            <div className="md:col-span-7 bg-white p-3 rounded-lg border border-slate-200">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
                Tailored Practical Precautions
              </h4>
              <ul className="space-y-1.5 text-xs text-slate-600">
                {advisoryData.precautions.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-1.5">
                    <span className="text-teal-600 font-bold shrink-0">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Symptoms to Watch */}
            <div className="md:col-span-5 bg-white p-3 rounded-lg border border-slate-200">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2 flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
                Symptoms To Watch For
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {advisoryData.symptoms_watch.map((sym, sIdx) => (
                  <span
                    key={sIdx}
                    className="text-[11px] px-2 py-1 rounded bg-amber-50 text-amber-900 border border-amber-200 font-medium"
                  >
                    {sym}
                  </span>
                ))}
              </div>
            </div>

          </div>

        </div>
      )}

    </div>
  );
};

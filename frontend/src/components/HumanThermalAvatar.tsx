import React from 'react';

interface HumanThermalAvatarProps {
  utci: number;
  categoryName: string;
  className?: string;
}

export const HumanThermalAvatar: React.FC<HumanThermalAvatarProps> = ({
  utci,
  categoryName,
  className = ''
}) => {
  // Determine state index based on project UTCI bands:
  // State 0: < 26°C (Comfortable / Relaxed)
  // State 1: 26 to < 32°C (Warm / Mild Discomfort)
  // State 2: 32 to < 38°C (Moderate to Strong Heat Stress / Noticeable sweating / wiping brow)
  // State 3: 38 to < 46°C (Very Strong Heat Stress / Obvious sweating & fanning)
  // State 4: >= 46°C (Extreme Heat Stress / Severe Heat Emergency Posture)
  let stateIndex = 0;
  if (utci >= 46.0) {
    stateIndex = 4;
  } else if (utci >= 38.0) {
    stateIndex = 3;
  } else if (utci >= 32.0) {
    stateIndex = 2;
  } else if (utci >= 26.0) {
    stateIndex = 1;
  } else {
    stateIndex = 0;
  }

  // Visual metadata per state
  const stateConfigs = [
    {
      label: 'Comfortable & Relaxed',
      badgeText: 'Low / No Thermal Discomfort',
      themeColor: '#16a34a',
      bgGlow: 'radial-gradient(circle, rgba(22, 163, 74, 0.12) 0%, rgba(240, 253, 244, 0) 70%)',
      accentBorder: 'border-emerald-200',
      tagBg: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      description: 'Human thermal comfort optimal; minimal physiological strain.'
    },
    {
      label: 'Warm & Mild Strain',
      badgeText: 'Moderate Thermal Sensation',
      themeColor: '#ca8a04',
      bgGlow: 'radial-gradient(circle, rgba(202, 138, 4, 0.14) 0%, rgba(254, 252, 232, 0) 70%)',
      accentBorder: 'border-yellow-200',
      tagBg: 'bg-yellow-50 text-yellow-800 border-yellow-200',
      description: 'Elevated ambient warmth; slight thermal discomfort beginning.'
    },
    {
      label: 'Noticeably Heat Stressed',
      badgeText: 'Active Thermoregulation',
      themeColor: '#ea580c',
      bgGlow: 'radial-gradient(circle, rgba(234, 88, 12, 0.15) 0%, rgba(255, 247, 237, 0) 70%)',
      accentBorder: 'border-orange-200',
      tagBg: 'bg-orange-50 text-orange-800 border-orange-200',
      description: 'Noticeable heat discomfort; sweating and wiping brow.'
    },
    {
      label: 'Strong Heat Stress',
      badgeText: 'High Physiological Strain',
      themeColor: '#dc2626',
      bgGlow: 'radial-gradient(circle, rgba(220, 38, 38, 0.18) 0%, rgba(254, 242, 242, 0) 70%)',
      accentBorder: 'border-red-200',
      tagBg: 'bg-red-50 text-red-800 border-red-200',
      description: 'Obvious heat distress; active fanning and shaded shelter required.'
    },
    {
      label: 'Extreme Heat Stress',
      badgeText: 'Severe Thermal Emergency',
      themeColor: '#991b1b',
      bgGlow: 'radial-gradient(circle, rgba(153, 27, 27, 0.22) 0%, rgba(254, 242, 242, 0) 70%)',
      accentBorder: 'border-rose-300',
      tagBg: 'bg-rose-100 text-rose-900 border-rose-300',
      description: 'Extreme thermal conditions; high risk of heat exhaustion.'
    }
  ];

  const currentConfig = stateConfigs[stateIndex];

  return (
    <div
      className={`relative flex flex-col items-center justify-center p-3 rounded-xl border transition-all duration-500 bg-white shadow-xs ${currentConfig.accentBorder} ${className}`}
      role="img"
      aria-label={`Human thermal visual representation: ${currentConfig.label} at UTCI ${utci.toFixed(1)}°C (${categoryName})`}
    >
      {/* Background Ambient Glow */}
      <div
        className="absolute inset-0 rounded-xl pointer-events-none transition-all duration-700 opacity-90"
        style={{ background: currentConfig.bgGlow }}
      />

      {/* SVG Character / Human Illustration */}
      <div className="relative w-28 h-36 flex items-center justify-center">
        <svg
          viewBox="0 0 160 200"
          className="w-full h-full drop-shadow-xs transition-transform duration-500"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Defs for gradients & filters */}
          <defs>
            <linearGradient id="skinGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#f6d3b3" />
              <stop offset="100%" stopColor="#e2b591" />
            </linearGradient>
            <linearGradient id="hairGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#334155" />
              <stop offset="100%" stopColor="#1e293b" />
            </linearGradient>
            <linearGradient id="shirtGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={currentConfig.themeColor} stopOpacity="0.85" />
              <stop offset="100%" stopColor={currentConfig.themeColor} stopOpacity="1" />
            </linearGradient>
            <linearGradient id="sweatGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="100%" stopColor="#0284c7" />
            </linearGradient>
          </defs>

          {/* Ambient Heat Wave / Sun Rays depending on state */}
          {stateIndex >= 2 && (
            <g className="animate-pulse opacity-70">
              {/* Sun icon / solar radiant waves at top-right */}
              <circle cx="135" cy="25" r="12" fill="#f59e0b" fillOpacity="0.25" />
              <circle cx="135" cy="25" r="7" fill="#f59e0b" />
              <line x1="135" y1="8" x2="135" y2="4" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" />
              <line x1="135" y1="42" x2="135" y2="46" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" />
              <line x1="118" y1="25" x2="114" y2="25" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" />
              <line x1="152" y1="25" x2="156" y2="25" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" />
              <line x1="123" y1="13" x2="120" y2="10" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="147" y1="37" x2="150" y2="40" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round" />
            </g>
          )}

          {/* State 4 Extreme: Heat Shimmer Waves */}
          {stateIndex === 4 && (
            <g opacity="0.6">
              <path d="M 20,40 Q 30,35 40,40 T 60,40" stroke="#ef4444" strokeWidth="1.5" fill="none" strokeLinecap="round" className="animate-pulse" />
              <path d="M 100,50 Q 110,45 120,50 T 140,50" stroke="#ef4444" strokeWidth="1.5" fill="none" strokeLinecap="round" className="animate-pulse" />
              <path d="M 30,170 Q 45,165 60,170 T 90,170" stroke="#ef4444" strokeWidth="1.5" fill="none" strokeLinecap="round" />
            </g>
          )}

          {/* Ground shadow */}
          <ellipse cx="80" cy="188" rx="36" ry="6" fill="#0f172a" fillOpacity="0.08" />

          {/* Legs & Shoes */}
          <path d="M 70 140 L 70 180" stroke="#475569" strokeWidth="10" strokeLinecap="round" />
          <path d="M 90 140 L 90 180" stroke="#475569" strokeWidth="10" strokeLinecap="round" />
          <path d="M 64 182 L 74 182" stroke="#1e293b" strokeWidth="6" strokeLinecap="round" />
          <path d="M 86 182 L 96 182" stroke="#1e293b" strokeWidth="6" strokeLinecap="round" />

          {/* Torso / Shirt */}
          <path
            d="M 60 85 Q 80 82 100 85 L 104 142 Q 80 146 56 142 Z"
            fill="url(#shirtGrad)"
            className="transition-colors duration-500"
          />

          {/* Collar */}
          <path d="M 72 84 L 80 94 L 88 84" stroke="#ffffff" strokeWidth="2" fill="none" strokeLinecap="round" />

          {/* Head & Neck */}
          <rect x="74" y="70" width="12" height="16" rx="4" fill="url(#skinGrad)" />
          
          {/* Head tilt and posture depending on heat stress */}
          <g transform={stateIndex >= 3 ? "rotate(6 80 50)" : stateIndex === 2 ? "rotate(3 80 50)" : "rotate(0 80 50)"}>
            {/* Head oval */}
            <ellipse cx="80" cy="52" rx="20" ry="23" fill="url(#skinGrad)" />

            {/* Hair */}
            <path
              d="M 60 50 C 60 30, 100 30, 100 50 C 96 40, 88 36, 80 36 C 72 36, 64 40, 60 50 Z"
              fill="url(#hairGrad)"
            />

            {/* Eyes & Eyebrows */}
            {stateIndex === 0 && (
              // State 0: Relaxed, pleasant smile
              <>
                {/* Eyes */}
                <ellipse cx="73" cy="50" rx="2.5" ry="3" fill="#1e293b" />
                <ellipse cx="87" cy="50" rx="2.5" ry="3" fill="#1e293b" />
                {/* Eyebrows */}
                <path d="M 70 44 Q 73 42 77 44" stroke="#334155" strokeWidth="1.5" strokeLinecap="round" fill="none" />
                <path d="M 83 44 Q 87 42 90 44" stroke="#334155" strokeWidth="1.5" strokeLinecap="round" fill="none" />
                {/* Gentle Smile */}
                <path d="M 74 62 Q 80 67 86 62" stroke="#9a3412" strokeWidth="1.8" strokeLinecap="round" fill="none" />
              </>
            )}

            {stateIndex === 1 && (
              // State 1: Warm, neutral expression
              <>
                <ellipse cx="73" cy="50" rx="2.5" ry="2.8" fill="#1e293b" />
                <ellipse cx="87" cy="50" rx="2.5" ry="2.8" fill="#1e293b" />
                <path d="M 70 44 L 76 44" stroke="#334155" strokeWidth="1.5" strokeLinecap="round" />
                <path d="M 84 44 L 90 44" stroke="#334155" strokeWidth="1.5" strokeLinecap="round" />
                {/* Straight neutral mouth */}
                <path d="M 75 63 L 85 63" stroke="#9a3412" strokeWidth="1.8" strokeLinecap="round" />
              </>
            )}

            {stateIndex === 2 && (
              // State 2: Heat stress, squinting, slight frown
              <>
                {/* Squinting eyes */}
                <path d="M 71 51 Q 74 48 77 51" stroke="#1e293b" strokeWidth="2" strokeLinecap="round" fill="none" />
                <path d="M 83 51 Q 86 48 89 51" stroke="#1e293b" strokeWidth="2" strokeLinecap="round" fill="none" />
                {/* Inward tilted eyebrows */}
                <path d="M 70 46 L 77 43" stroke="#334155" strokeWidth="1.8" strokeLinecap="round" />
                <path d="M 90 46 L 83 43" stroke="#334155" strokeWidth="1.8" strokeLinecap="round" />
                {/* Strained mouth */}
                <path d="M 75 64 Q 80 60 85 64" stroke="#9a3412" strokeWidth="1.8" strokeLinecap="round" fill="none" />
                {/* Sweat droplet on forehead */}
                <path d="M 68 40 Q 66 43 68 45 Q 70 43 68 40 Z" fill="url(#sweatGrad)" />
              </>
            )}

            {stateIndex === 3 && (
              // State 3: Strong heat stress, panting/open mouth, multiple sweat drops
              <>
                <path d="M 71 52 Q 74 49 77 52" stroke="#1e293b" strokeWidth="2.2" strokeLinecap="round" fill="none" />
                <path d="M 83 52 Q 86 49 89 52" stroke="#1e293b" strokeWidth="2.2" strokeLinecap="round" fill="none" />
                <path d="M 69 47 L 77 43" stroke="#334155" strokeWidth="2" strokeLinecap="round" />
                <path d="M 91 47 L 83 43" stroke="#334155" strokeWidth="2" strokeLinecap="round" />
                {/* Panting open mouth */}
                <ellipse cx="80" cy="64" rx="4" ry="3" fill="#881337" />
                {/* Sweat drops */}
                <path d="M 66 38 Q 64 42 66 45 Q 68 42 66 38 Z" fill="url(#sweatGrad)" />
                <path d="M 94 42 Q 92 46 94 49 Q 96 46 94 42 Z" fill="url(#sweatGrad)" />
                <path d="M 63 56 Q 61 59 63 62 Q 65 59 63 56 Z" fill="url(#sweatGrad)" />
              </>
            )}

            {stateIndex === 4 && (
              // State 4: Extreme stress, exhausted posture, heavy perspiration
              <>
                <path d="M 70 53 Q 74 50 78 53" stroke="#1e293b" strokeWidth="2.5" strokeLinecap="round" fill="none" />
                <path d="M 82 53 Q 86 50 90 53" stroke="#1e293b" strokeWidth="2.5" strokeLinecap="round" fill="none" />
                <path d="M 68 48 L 78 43" stroke="#1e293b" strokeWidth="2.2" strokeLinecap="round" />
                <path d="M 92 48 L 82 43" stroke="#1e293b" strokeWidth="2.2" strokeLinecap="round" />
                {/* Gaspeing mouth */}
                <ellipse cx="80" cy="65" rx="5.5" ry="4" fill="#7f1d1d" />
                {/* Heavy sweat dripping */}
                <path d="M 64 36 Q 61 41 64 45 Q 67 41 64 36 Z" fill="url(#sweatGrad)" />
                <path d="M 96 38 Q 93 43 96 47 Q 99 43 96 38 Z" fill="url(#sweatGrad)" />
                <path d="M 61 54 Q 58 58 61 62 Q 64 58 61 54 Z" fill="url(#sweatGrad)" />
                <path d="M 98 56 Q 95 60 98 64 Q 101 60 98 56 Z" fill="url(#sweatGrad)" />
              </>
            )}
          </g>

          {/* Arms and Posture depending on state */}
          {stateIndex <= 1 && (
            // State 0 & 1: Arms relaxed at side
            <>
              <path d="M 60 90 L 48 130" stroke="url(#skinGrad)" strokeWidth="8" strokeLinecap="round" />
              <path d="M 100 90 L 112 130" stroke="url(#skinGrad)" strokeWidth="8" strokeLinecap="round" />
            </>
          )}

          {stateIndex === 2 && (
            // State 2: One arm wiping forehead, one at side
            <>
              {/* Left arm wiping brow */}
              <path d="M 60 92 Q 44 80 62 48" stroke="url(#skinGrad)" strokeWidth="8" strokeLinecap="round" fill="none" />
              <circle cx="64" cy="46" r="5" fill="url(#skinGrad)" />
              {/* Right arm at side */}
              <path d="M 100 90 L 112 130" stroke="url(#skinGrad)" strokeWidth="8" strokeLinecap="round" />
            </>
          )}

          {stateIndex === 3 && (
            // State 3: Arm wiping brow + other arm fanning self
            <>
              {/* Left arm wiping brow */}
              <path d="M 60 92 Q 42 78 64 46" stroke="url(#skinGrad)" strokeWidth="8" strokeLinecap="round" fill="none" />
              <circle cx="66" cy="44" r="5" fill="url(#skinGrad)" />
              {/* Right arm fanning with folded paper/hand */}
              <path d="M 100 90 Q 120 105 110 80" stroke="url(#skinGrad)" strokeWidth="8" strokeLinecap="round" fill="none" />
              {/* Small hand fan */}
              <path d="M 108 76 L 122 66 L 126 78 Z" fill="#e2e8f0" stroke="#94a3b8" strokeWidth="1" />
            </>
          )}

          {stateIndex === 4 && (
            // State 4: Both hands shielding head / holding neck in severe heat
            <>
              {/* Left hand shielding forehead */}
              <path d="M 60 94 Q 40 70 70 42" stroke="url(#skinGrad)" strokeWidth="8" strokeLinecap="round" fill="none" />
              {/* Right hand on chest/neck */}
              <path d="M 100 94 Q 115 85 86 86" stroke="url(#skinGrad)" strokeWidth="8" strokeLinecap="round" fill="none" />
            </>
          )}
        </svg>
      </div>

      {/* State Caption & Subtle Physiological Label */}
      <div className="mt-2 text-center w-full">
        <span
          className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wide ${currentConfig.tagBg}`}
        >
          {currentConfig.label}
        </span>
        <p className="text-[10px] text-slate-500 font-medium mt-1 leading-tight max-w-[130px] mx-auto">
          {currentConfig.description}
        </p>
      </div>
    </div>
  );
};

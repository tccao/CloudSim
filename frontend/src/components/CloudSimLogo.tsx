// =============================================================================
// CloudSimLogo.tsx
// =============================================================================
// A presentational component that renders the CloudSim brand logo with an SVG
// cloud icon and gradient text.
//
// API CALLS: None
//
// COMPONENT STRUCTURE:
// └── CloudSimLogo
//     ├── SVG Cloud Icon (gradient orange)
//     └── Brand Text ("CloudSim" + tagline)
// =============================================================================


// =============================================================================
// COMPONENT
// =============================================================================

export function CloudSimLogo() {
  return (
    <div className="flex items-center gap-3">
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="cloudGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#fb923c', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#f97316', stopOpacity: 1 }} />
          </linearGradient>
        </defs>
        {/* Cloud shape */}
        <path
          d="M38 24c0-1.5-.4-2.9-1-4.1 0-4.4-3.6-8-8-8-2.5 0-4.7 1.1-6.2 2.9C21.6 14.3 20.4 14 19 14c-4.4 0-8 3.6-8 8 0 .3 0 .6.1.9C8.9 23.8 7 26.2 7 29c0 3.9 3.1 7 7 7h22c3.9 0 7-3.1 7-7 0-3.5-2.6-6.4-6-6.9z"
          fill="url(#cloudGradient)"
          opacity="0.9"
        />
        {/* Curved line underneath */}
        <path
          d="M12 38 Q24 34 36 38"
          stroke="url(#cloudGradient)"
          strokeWidth="2"
          fill="none"
          strokeLinecap="round"
        />
      </svg>
      <div>
        <h1 className="text-2xl bg-gradient-to-r from-orange-400 to-orange-600 bg-clip-text text-transparent">
          CloudSim
        </h1>
        <p className="text-xs text-gray-600">Simulate. Deploy. Scale.</p>
      </div>
    </div>
  );
}

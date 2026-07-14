export const IMPACT_COLORS = {
  Bullish: '#059669',
  Bearish: '#dc2626',
  Mixed: '#8b5cf6',
  Neutral: '#d97706',
  Uncertain: '#64748b',
};

export const IMPACT_BG_COLORS = {
  Bullish: 'rgba(5, 150, 105, 0.1)',
  Bearish: 'rgba(220, 38, 38, 0.1)',
  Mixed: 'rgba(139, 92, 246, 0.1)',
  Neutral: 'rgba(217, 119, 6, 0.1)',
  Uncertain: 'rgba(100, 116, 139, 0.1)',
};

export const IMPACT_GLOWS = {
  Bullish: '0 0 12px rgba(5, 150, 105, 0.25)',
  Bearish: '0 0 12px rgba(220, 38, 38, 0.25)',
  Mixed: '0 0 12px rgba(139, 92, 246, 0.25)',
  Neutral: '0 0 12px rgba(217, 119, 6, 0.25)',
  Uncertain: '0 0 12px rgba(100, 116, 139, 0.15)',
};

export const IMPACT_EMOJIS = {
  Bullish: '🟢',
  Bearish: '🔴',
  Mixed: '🟣',
  Neutral: '🟡',
  Uncertain: '⚪',
};

// Normalize legacy Positive/Negative to Bullish/Bearish
function normalizeImpactKey(impact) {
  if (!impact) return 'Uncertain';
  let raw = impact.charAt(0).toUpperCase() + impact.slice(1).toLowerCase();
  if (raw === 'Positive') return 'Bullish';
  if (raw === 'Negative') return 'Bearish';
  if (raw === 'Unknown') return 'Uncertain';
  return raw;
}

export function getImpactColor(impact) {
  const key = normalizeImpactKey(impact);
  return IMPACT_COLORS[key] || IMPACT_COLORS.Unknown;
}

export function getImpactBgColor(impact) {
  const key = normalizeImpactKey(impact);
  return IMPACT_BG_COLORS[key] || IMPACT_BG_COLORS.Unknown;
}

export function getImpactEmoji(impact) {
  const key = normalizeImpactKey(impact);
  return IMPACT_EMOJIS[key] || IMPACT_EMOJIS.Unknown;
}

export function getImpactGlow(impact) {
  const key = normalizeImpactKey(impact);
  return IMPACT_GLOWS[key] || IMPACT_GLOWS.Unknown;
}

export function getImpactLabel(impact) {
  const key = normalizeImpactKey(impact);
  return key in IMPACT_COLORS ? key : 'Uncertain';
}

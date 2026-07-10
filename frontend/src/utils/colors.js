export const IMPACT_COLORS = {
  Positive: '#059669',
  Negative: '#dc2626',
  Neutral: '#d97706',
  Unknown: '#64748b',
};

export const IMPACT_BG_COLORS = {
  Positive: 'rgba(5, 150, 105, 0.1)',
  Negative: 'rgba(220, 38, 38, 0.1)',
  Neutral: 'rgba(217, 119, 6, 0.1)',
  Unknown: 'rgba(100, 116, 139, 0.1)',
};

export const IMPACT_GLOWS = {
  Positive: '0 0 12px rgba(5, 150, 105, 0.25)',
  Negative: '0 0 12px rgba(220, 38, 38, 0.25)',
  Neutral: '0 0 12px rgba(217, 119, 6, 0.25)',
  Unknown: '0 0 12px rgba(100, 116, 139, 0.15)',
};

export const IMPACT_EMOJIS = {
  Positive: '🟢',
  Negative: '🔴',
  Neutral: '🟡',
  Unknown: '⚪',
};

// Normalize legacy Bullish/Bearish to Positive/Negative
function normalizeImpactKey(impact) {
  if (!impact) return 'Unknown';
  const raw = impact.charAt(0).toUpperCase() + impact.slice(1).toLowerCase();
  if (raw === 'Bullish') return 'Positive';
  if (raw === 'Bearish') return 'Negative';
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
  return key in IMPACT_COLORS ? key : 'Unknown';
}

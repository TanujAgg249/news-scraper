import React, { memo, useState, useEffect, useMemo, useCallback } from 'react';
import { fetchOilPrice } from '../api/client';
import './OilPriceWidget.css';

const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

function generateSparklinePath(prices, width, height) {
  if (!prices || prices.length < 2) return { line: '', area: '' };

  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const step = width / (prices.length - 1);

  const points = prices.map((p, i) => ({
    x: i * step,
    y: height - ((p - min) / range) * height,
  }));

  const line = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');
  const area =
    line +
    ` L${points[points.length - 1].x},${height} L${points[0].x},${height} Z`;

  return { line, area };
}

const OilPriceWidget = memo(function OilPriceWidget() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  const loadPrice = useCallback(async () => {
    try {
      const result = await fetchOilPrice();
      setData(result);
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    loadPrice();
    const interval = setInterval(loadPrice, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [loadPrice]);

  const latest = data?.latest;
  const price = latest?.price ?? null;
  const change = latest?.change ?? 0;
  const changePct = latest?.change_pct ?? 0;
  const historyRaw = data?.history ?? [];
  const history = historyRaw.map(h => h.price);
  const label = 'Brent Crude';
  const isUp = change >= 0;
  const color = isUp ? 'var(--bullish)' : 'var(--bearish)';

  const sparkline = useMemo(() => {
    if (history.length < 2) return null;
    return generateSparklinePath(history, 200, 28);
  }, [history]);

  if (error && !data) {
    return (
      <div className="oil-price-widget">
        <div className="oil-price-card">
          <div className="oil-price-header">
            <span className="oil-price-label">Brent Crude</span>
          </div>
          <span className="oil-price-unavailable">Price unavailable</span>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="oil-price-widget">
        <div className="oil-price-card">
          <div className="oil-price-header">
            <span className="oil-price-label">Brent Crude</span>
            <span className="oil-price-live">
              <span className="oil-price-live-dot" />
              Live
            </span>
          </div>
          <span className="oil-price-unavailable" style={{ opacity: 0.4 }}>
            Loading…
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="oil-price-widget">
      <div className="oil-price-card" style={{ boxShadow: isUp ? 'var(--glow-bullish)' : 'var(--glow-bearish)' }}>
        <div className="oil-price-header">
          <span className="oil-price-label">{label}</span>
          <span className="oil-price-live">
            <span className="oil-price-live-dot" />
            Live
          </span>
        </div>

        <div className="oil-price-row">
          <span className="oil-price-value" style={{ color }}>
            ${price !== null ? Number(price).toFixed(2) : '—'}
          </span>
          <span className="oil-price-change" style={{ color }}>
            {isUp ? '▲' : '▼'} {isUp ? '+' : ''}
            ${Math.abs(change).toFixed(2)} ({isUp ? '+' : ''}
            {Number(changePct).toFixed(2)}%)
          </span>
        </div>

        {sparkline && (
          <svg
            className="oil-price-sparkline"
            viewBox="0 0 200 28"
            preserveAspectRatio="none"
          >
            <path
              className="oil-price-sparkline-area"
              d={sparkline.area}
              fill={isUp ? 'var(--bullish)' : 'var(--bearish)'}
            />
            <path
              className="oil-price-sparkline-line"
              d={sparkline.line}
              stroke={isUp ? 'var(--bullish)' : 'var(--bearish)'}
            />
          </svg>
        )}
      </div>
    </div>
  );
});

export default OilPriceWidget;

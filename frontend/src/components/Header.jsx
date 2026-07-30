import React, { memo, useCallback } from 'react';
import './Header.css';

const TIME_RANGES = [
  { label: '1H', hours: 1 },
  { label: '6H', hours: 6 },
  { label: '24H', hours: 24 },
  { label: '48H', hours: 48 },
  { label: 'ALL', hours: 0 },
];

const Header = memo(function Header({
  theme,
  onThemeToggle,
  onManageTopics,
  timeRange,
  onTimeRangeChange,
}) {
  const handleTimeClick = useCallback((hours) => {
    // Toggle off if already selected
    onTimeRangeChange(timeRange === hours ? null : hours);
  }, [timeRange, onTimeRangeChange]);

  return (
    <header className="header">
      <div className="header-left">
        <div className="header-logo">
          <div className="header-logo-icon">⚡</div>
          <h1 className="header-title">EnergyPulse</h1>
        </div>
      </div>

      {/* Time Range Selector */}
      <nav className="header-center">
        <span className="time-range-label">
          <svg className="time-range-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
        </span>
        {TIME_RANGES.map(({ label, hours }) => (
          <button
            key={hours}
            className={`time-range-btn ${timeRange === hours ? 'active' : ''}`}
            onClick={() => handleTimeClick(hours)}
            title={`Show articles from the past ${hours} hour${hours > 1 ? 's' : ''}`}
          >
            {label}
          </button>
        ))}
      </nav>

      <div className="header-right">
        <button className="header-btn theme-toggle" onClick={onThemeToggle} aria-label="Toggle theme">
          <span className="header-btn-icon">{theme === 'dark' ? '☀️' : '🌙'}</span>
        </button>
        <button className="header-btn" onClick={onManageTopics}>
          <span className="header-btn-icon">⚙</span>
          Topics
        </button>
      </div>
    </header>
  );
});

export default Header;

import React, { memo, useCallback, useMemo, useRef, useState, useEffect } from 'react';
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  ZoomableGroup,
} from 'react-simple-maps';
import { getImpactColor, getImpactEmoji, getImpactBgColor } from '../utils/colors';
import './WorldMap.css';

const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

const WorldMap = memo(function WorldMap({
  graphData,
  onNodeClick,
  selectedNodeId,
  loading,
  error,
  onRetry,
  theme,
}) {
  const [tooltip, setTooltip] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [position, setPosition] = useState({ coordinates: [20, 20], zoom: 1 });
  const containerRef = useRef(null);

  // Track mouse for tooltip positioning
  useEffect(() => {
    const handler = (e) => setMousePos({ x: e.clientX, y: e.clientY });
    window.addEventListener('mousemove', handler);
    return () => window.removeEventListener('mousemove', handler);
  }, []);

  // Filter nodes with valid coordinates
  const geoNodes = useMemo(() => {
    if (!graphData || !graphData.nodes) return [];
    return graphData.nodes.filter(
      (n) =>
        n.latitude != null &&
        n.longitude != null &&
        !isNaN(n.latitude) &&
        !isNaN(n.longitude)
    );
  }, [graphData]);

  // Count unique locations
  const locationCount = useMemo(() => {
    const locs = new Set(geoNodes.map((n) => n.location || 'Unknown'));
    return locs.size;
  }, [geoNodes]);

  const handleMarkerClick = useCallback(
    (node) => {
      if (onNodeClick) onNodeClick(node);
    },
    [onNodeClick]
  );

  const handleMarkerEnter = useCallback((node) => {
    setTooltip({
      headline: node.headline || 'Untitled',
      source: node.source || 'Unknown',
      impact: node.oil_impact || 'Unknown',
      location: node.location || 'Unknown',
    });
  }, []);

  const handleMarkerLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  const handleMoveEnd = useCallback((pos) => {
    setPosition(pos);
  }, []);

  // Loading state
  if (loading && (!graphData || !graphData.nodes || graphData.nodes.length === 0)) {
    return (
      <div className="map-container">
        <div className="map-loading">
          <div className="map-spinner" />
          <span className="map-loading-text">Loading map data…</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="map-container">
        <div className="map-error">
          <span className="map-error-icon">⚠️</span>
          <span className="map-error-text">{error}</span>
          <button className="map-retry-btn" onClick={onRetry}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Empty state
  if (geoNodes.length === 0) {
    return (
      <div className="map-container">
        <div className="map-empty">
          <span className="map-empty-icon">🗺️</span>
          <span className="map-empty-text">
            No geo-located articles yet.
            <br />
            Articles will appear as they are scraped.
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="map-container" ref={containerRef}>
      {/* Stats */}
      <div className="map-stats">
        <span className="map-stats-item">
          📍 {geoNodes.length} articles
        </span>
        <span className="map-stats-sep">•</span>
        <span className="map-stats-item">
          🌍 {locationCount} locations
        </span>
      </div>

      <ComposableMap
        projection="geoMercator"
        projectionConfig={{
          scale: 130,
          center: [20, 20],
        }}
        style={{ width: '100%', height: '100%' }}
      >
        <ZoomableGroup
          zoom={position.zoom}
          center={position.coordinates}
          onMoveEnd={handleMoveEnd}
          minZoom={1}
          maxZoom={8}
        >
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  fill={theme === 'dark' ? '#334155' : '#e2e8f0'}
                  stroke={theme === 'dark' ? '#475569' : '#cbd5e1'}
                  strokeWidth={0.5}
                  style={{
                    default: { outline: 'none' },
                    hover: { fill: theme === 'dark' ? '#475569' : '#cbd5e1', outline: 'none' },
                    pressed: { outline: 'none' },
                  }}
                />
              ))
            }
          </Geographies>

          {geoNodes.map((node) => {
            const isSelected = node.id === selectedNodeId;
            const radius = Math.max(
              4,
              Math.min(12, ((node.importance_score || 50) / 100) * 12)
            );
            const color = getImpactColor(node.oil_impact || 'Unknown');

            return (
              <Marker
                key={node.id}
                coordinates={[node.longitude, node.latitude]}
                onClick={() => handleMarkerClick(node)}
                onMouseEnter={() => handleMarkerEnter(node)}
                onMouseLeave={handleMarkerLeave}
                style={{ cursor: 'pointer' }}
              >
                {/* Outer glow ring */}
                <circle
                  r={radius + 3}
                  fill={color}
                  fillOpacity={isSelected ? 0.3 : 0.15}
                  stroke="none"
                />
                {/* Main circle */}
                <circle
                  r={radius}
                  fill={color}
                  fillOpacity={0.85}
                  stroke="#fff"
                  strokeWidth={isSelected ? 2.5 : 1.5}
                />
                {/* Selected indicator */}
                {isSelected && (
                  <circle
                    r={radius + 6}
                    fill="none"
                    stroke={color}
                    strokeWidth={1.5}
                    strokeDasharray="3 2"
                    opacity={0.6}
                  />
                )}
              </Marker>
            );
          })}
        </ZoomableGroup>
      </ComposableMap>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="map-tooltip"
          style={{
            left: mousePos.x + 15,
            top: mousePos.y - 10,
          }}
        >
          <div className="map-tooltip-headline">{tooltip.headline}</div>
          <div className="map-tooltip-meta">
            <span>{tooltip.source}</span>
            <span className="map-tooltip-sep">•</span>
            <span
              className="map-tooltip-impact"
              style={{ color: getImpactColor(tooltip.impact) }}
            >
              {getImpactEmoji(tooltip.impact)} {tooltip.impact}
            </span>
          </div>
          <div className="map-tooltip-location">📍 {tooltip.location}</div>
          <div className="map-tooltip-hint">Click to view details</div>
        </div>
      )}
    </div>
  );
});

export default WorldMap;

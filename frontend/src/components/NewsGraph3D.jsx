import React, { memo, useCallback, useMemo, useRef, useState, useEffect } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import * as THREE from 'three';
import { getImpactColor, getImpactEmoji, getImpactBgColor } from '../utils/colors';
import './NewsGraph3D.css';

const NODE_MIN_SIZE = 3;
const NODE_MAX_SIZE = 18;

function mapImportance(score) {
  const s = score || 0;
  const clamped = Math.max(0, Math.min(1, s / 10));
  return NODE_MIN_SIZE + clamped * (NODE_MAX_SIZE - NODE_MIN_SIZE);
}

function getSizeCategory(size) {
  if (size < 6) return 'sm';
  if (size < 12) return 'md';
  return 'lg';
}

const NewsGraph3D = memo(function NewsGraph3D({
  graphData,
  onNodeClick,
  selectedNodeId,
  loading,
  error,
  onRetry,
  theme,
}) {
  const graphRef = useRef(null);
  const containerRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [showHint, setShowHint] = useState(true);
  const lastClickRef = useRef({ nodeId: null, time: 0 });
  const autoRotateTimeoutRef = useRef(null);
  const cacheRef = useRef(new Map());
  // Track pinned (dragged) node positions
  const [hasPinnedNodes, setHasPinnedNodes] = useState(false);
  const pinnedSetRef = useRef(new Set());

  // Resize observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({ width: Math.floor(width), height: Math.floor(height) });
      }
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // Auto-dismiss interaction hint after 8 seconds
  useEffect(() => {
    if (!showHint) return;
    const timer = setTimeout(() => setShowHint(false), 8000);
    return () => clearTimeout(timer);
  }, [showHint]);

  const dismissHint = useCallback(() => setShowHint(false), []);

  // Auto-rotate camera + pause on interaction
  useEffect(() => {
    const fg = graphRef.current;
    if (!fg) return;

    const controls = fg.controls();
    if (controls) {
      controls.autoRotate = true;
      controls.autoRotateSpeed = 0.5;
      controls.enableDamping = true;
      controls.dampingFactor = 0.25;
    }

    const renderer = fg.renderer();
    const domElement = renderer && renderer.domElement;
    if (!domElement) return;

    const pauseAutoRotate = () => {
      if (controls) controls.autoRotate = false;
      if (autoRotateTimeoutRef.current) {
        clearTimeout(autoRotateTimeoutRef.current);
      }
      autoRotateTimeoutRef.current = setTimeout(() => {
        if (controls) controls.autoRotate = true;
      }, 5000);
    };

    domElement.addEventListener('mousedown', pauseAutoRotate);
    domElement.addEventListener('touchstart', pauseAutoRotate);

    return () => {
      domElement.removeEventListener('mousedown', pauseAutoRotate);
      domElement.removeEventListener('touchstart', pauseAutoRotate);
      if (autoRotateTimeoutRef.current) {
        clearTimeout(autoRotateTimeoutRef.current);
      }
    };
  }, [graphData]);

  // Whenever graphData changes, we need to tell ForceGraph to update nodes
  // because their properties (like oil_impact) might have changed from a refetch.
  const updateTrigger = graphData ? graphData.nodes.map(n => n.oil_impact).join(',') : '';

  // Cleanup cached geometries/materials on unmount
  useEffect(() => {
    const cache = cacheRef.current;
    return () => {
      cache.forEach((entry) => {
        if (entry.geometry) entry.geometry.dispose();
        if (entry.material) entry.material.dispose();
        if (entry.glowGeometry) entry.glowGeometry.dispose();
        if (entry.glowMaterial) entry.glowMaterial.dispose();
      });
      cache.clear();
    };
  }, []);

  const handleNodeHover = useCallback((node, prevNode) => {
    if (node) {
      setTooltip({
        headline: node.headline || node.title || 'Untitled',
        source: node.source || 'Unknown',
        impact: node.oil_impact || node.impact || 'Unknown',
        url: node.url || null,
        x: 0,
        y: 0,
      });
    } else {
      setTooltip(null);
    }
    // Change cursor
    const el = document.querySelector('.graph-canvas-wrap canvas');
    if (el) {
      el.style.cursor = node ? 'pointer' : 'default';
    }
  }, []);

  const handlePointerMove = useCallback((e) => {
    setTooltip((prev) => {
      if (!prev) return null;
      return { ...prev, x: e.clientX, y: e.clientY };
    });
  }, []);

  const handleNodeClick = useCallback(
    (node) => {
      const now = Date.now();
      const last = lastClickRef.current;

      // Double-click detection: same node within 400ms
      if (last.nodeId === node.id && now - last.time < 400) {
        // Double click → open URL
        const url = node.url;
        if (url) {
          window.open(url, '_blank', 'noopener,noreferrer');
        }
        lastClickRef.current = { nodeId: null, time: 0 };
        return;
      }

      // Record this click
      lastClickRef.current = { nodeId: node.id, time: now };

      // Single click behavior
      if (onNodeClick) onNodeClick(node);

      // Fly camera to node
      const fg = graphRef.current;
      if (fg && node.x !== undefined) {
        const distance = 120;
        const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z || 0);
        fg.cameraPosition(
          { x: node.x * distRatio, y: node.y * distRatio, z: (node.z || 0) * distRatio },
          { x: node.x, y: node.y, z: node.z || 0 },
          1000
        );
      }
    },
    [onNodeClick]
  );

  // Node drag end: pin the node in place
  const handleNodeDragEnd = useCallback((node) => {
    // Fix the node position so it doesn't move
    node.fx = node.x;
    node.fy = node.y;
    node.fz = node.z;
    // Track it so we can reset later
    pinnedSetRef.current.add(node.id);
    setHasPinnedNodes(true);
  }, []);

  // Reset all pinned positions and reheat the simulation
  const handleResetLayout = useCallback(() => {
    const fg = graphRef.current;
    if (!fg) return;
    // Unpin all nodes
    graphData.nodes.forEach((node) => {
      delete node.fx;
      delete node.fy;
      delete node.fz;
    });
    pinnedSetRef.current.clear();
    setHasPinnedNodes(false);
    // Reheat the simulation to let nodes settle naturally
    fg.d3ReheatSimulation();
  }, [graphData]);

  // Custom node rendering with Three.js + caching
  const nodeThreeObject = useCallback(
    (node) => {
      const impact = node.oil_impact || node.impact || 'Unknown';
      const color = getImpactColor(impact);
      const size = mapImportance(node.importance_score);
      const finalSize = node.event_type === 'primary' ? size * 1.5 : size;
      const isSelected = selectedNodeId && node.id === selectedNodeId;
      const sizeCat = getSizeCategory(finalSize);
      const cacheKey = `${impact}-${sizeCat}-${isSelected}`;

      let cached = cacheRef.current.get(cacheKey);
      if (!cached) {
        const geometry = new THREE.SphereGeometry(finalSize * 0.6, 16, 12);
        const material = new THREE.MeshPhongMaterial({
          color: new THREE.Color(color),
          emissive: new THREE.Color(color),
          emissiveIntensity: isSelected ? 0.8 : 0.3,
          transparent: true,
          opacity: isSelected ? 1 : 0.85,
          shininess: 60,
        });
        cached = { geometry, material };

        if (isSelected) {
          cached.glowGeometry = new THREE.SphereGeometry(finalSize * 0.9, 16, 12);
          cached.glowMaterial = new THREE.MeshBasicMaterial({
            color: new THREE.Color(color),
            transparent: true,
            opacity: 0.15,
          });
        }

        cacheRef.current.set(cacheKey, cached);
      }

      const mesh = new THREE.Mesh(cached.geometry, cached.material);

      if (isSelected && cached.glowGeometry && cached.glowMaterial) {
        const glowMesh = new THREE.Mesh(cached.glowGeometry, cached.glowMaterial);
        mesh.add(glowMesh);
      }

      return mesh;
    },
    [selectedNodeId, updateTrigger]
  );

  const linkColor = useCallback((link) => {
    const similarity = link.similarity || link.weight || 0.3;
    const alpha = Math.max(0.05, Math.min(0.3, similarity * 0.5));
    return `rgba(100, 150, 255, ${alpha})`;
  }, []);

  const linkWidth = useCallback((link) => {
    const similarity = link.similarity || link.weight || 0.3;
    return Math.max(0.3, similarity * 2);
  }, []);

  // Render loading state
  if (loading && (!graphData || graphData.nodes.length === 0)) {
    return (
      <div className="graph-container" ref={containerRef}>
        <div className="graph-loading">
          <div className="graph-spinner" />
          <span className="graph-loading-text">Loading intelligence graph…</span>
        </div>
      </div>
    );
  }

  // Render error state
  if (error && (!graphData || graphData.nodes.length === 0)) {
    return (
      <div className="graph-container" ref={containerRef}>
        <div className="graph-error">
          <span className="graph-error-icon">⚠️</span>
          <p className="graph-error-text">{error}</p>
          {onRetry && (
            <button className="graph-error-retry" onClick={onRetry}>
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  // Render empty state
  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="graph-container" ref={containerRef}>
        <div className="graph-empty">
          <span className="graph-empty-icon">🌐</span>
          <p className="graph-empty-text">No data available. Add topics to start tracking.</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="graph-container"
      ref={containerRef}
      onPointerMove={handlePointerMove}
    >
      <div className="graph-canvas-wrap">
        <ForceGraph3D
          ref={graphRef}
          graphData={graphData}
          width={dimensions.width}
          height={dimensions.height}
          backgroundColor={theme === 'dark' ? '#0f172a' : '#f8fafc'}
          nodeThreeObject={nodeThreeObject}
          nodeThreeObjectExtend={false}
          onNodeClick={handleNodeClick}
          onNodeHover={handleNodeHover}
          onNodeDragEnd={handleNodeDragEnd}
          linkColor={linkColor}
          linkWidth={linkWidth}
          linkOpacity={0.4}
          linkDirectionalParticles={2}
          linkDirectionalParticleSpeed={0.003}
          linkDirectionalParticleWidth={1.5}
          linkDirectionalParticleColor={() => 'rgba(100, 180, 255, 0.6)'}
          d3AlphaDecay={0.03}
          d3VelocityDecay={0.4}
          warmupTicks={50}
          cooldownTicks={100}
          enableNodeDrag={true}
          showNavInfo={false}
        />
      </div>

      <div className="graph-depth-overlay" />

      {/* Interaction Hint */}
      {showHint && (
        <div className="graph-interaction-hint" onMouseDown={dismissHint} onTouchStart={dismissHint}>
          <span>🖱️ Drag nodes to rearrange</span>
          <span className="graph-hint-sep">·</span>
          <span>Click to read</span>
          <span className="graph-hint-sep">·</span>
          <span>Double-click to open article</span>
        </div>
      )}

      {/* Reset Layout Button */}
      {hasPinnedNodes && (
        <button className="graph-reset-btn" onClick={handleResetLayout} title="Reset all nodes to default positions">
          ↺ Reset Layout
        </button>
      )}

      {/* Stats badges */}
      <div className="graph-stats">
        <span className="graph-stat">{graphData.nodes.length} nodes</span>
        <span className="graph-stat">{graphData.links.length} links</span>
      </div>

      {/* Tooltip */}
      {tooltip && tooltip.x > 0 && (
        <div
          className="graph-tooltip"
          style={{
            left: tooltip.x + 14,
            top: tooltip.y - 10,
          }}
        >
          <div className="graph-tooltip-headline">{tooltip.headline}</div>
          <div className="graph-tooltip-meta">
            <span>{tooltip.source}</span>
            <span
              className="graph-tooltip-badge"
              style={{
                color: getImpactColor(tooltip.impact),
                background: getImpactBgColor(tooltip.impact),
              }}
            >
              {getImpactEmoji(tooltip.impact)} {tooltip.impact}
            </span>
          </div>
          <div className="graph-tooltip-hint">Click to read →</div>
        </div>
      )}
    </div>
  );
});

export default NewsGraph3D;

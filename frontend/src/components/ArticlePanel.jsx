import React, { memo, useCallback, useEffect, useState } from 'react';
import {
  getImpactColor,
  getImpactEmoji,
  getImpactBgColor,
  getImpactLabel,
} from '../utils/colors';
import { reclassifyArticle } from '../api/client';
import './ArticlePanel.css';

const IMPACT_OPTIONS = ['Bullish', 'Bearish', 'Neutral', 'Mixed', 'Uncertain'];

function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

const ArticlePanel = memo(function ArticlePanel({ article, onClose, onReclassify }) {
  const [closing, setClosing] = useState(false);
  const [currentImpact, setCurrentImpact] = useState(null);
  const [saving, setSaving] = useState(false);

  // Sync impact from article prop
  useEffect(() => {
    if (article) {
      setCurrentImpact(getImpactLabel(article.oil_impact || article.impact));
    }
  }, [article]);

  const handleClose = useCallback(() => {
    setClosing(true);
    setTimeout(() => {
      onClose();
    }, 250);
  }, [onClose]);

  const handleReclassify = useCallback(async (newImpact) => {
    if (!article?.id || saving) return;
    setSaving(true);
    try {
      await reclassifyArticle(article.id, newImpact);
      setCurrentImpact(newImpact);
      if (onReclassify) {
        onReclassify(article.id, newImpact);
      }
    } catch (err) {
      console.error('Reclassification failed:', err);
    } finally {
      setSaving(false);
    }
  }, [article, saving, onReclassify]);

  // Escape key handler
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') handleClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleClose]);

  if (!article) return null;

  const impactColor = getImpactColor(currentImpact);
  const impactBg = getImpactBgColor(currentImpact);
  const confidence = article.impact_confidence || article.confidence_score || 0;
  const confidencePct = Math.round(confidence * 100);
  const importance = article.importance_score || article.importance || 0;

  return (
    <>
      <div className="article-panel-backdrop" onClick={handleClose} />
      <aside className={`article-panel ${closing ? 'closing' : ''}`}>
        <div className="panel-header">
          <span className="panel-header-label">Article Detail</span>
          <button className="panel-close" onClick={handleClose} aria-label="Close">
            ✕
          </button>
        </div>

        <div className="panel-body">
          {/* Headline */}
          <h2 className="panel-headline">
            {article.headline || article.title || 'Untitled Article'}
          </h2>

          {/* Source & Date */}
          <div className="panel-meta">
            <span className="panel-source">{article.source || 'Unknown Source'}</span>
            {article.published_at && (
              <>
                <span className="panel-meta-sep" />
                <span className="panel-date">{formatDate(article.published_at)}</span>
              </>
            )}
          </div>

          {/* Current Impact Badge */}
          <div
            className="panel-impact-badge"
            style={{ color: impactColor, background: impactBg }}
          >
            {getImpactEmoji(currentImpact)} {currentImpact}
          </div>

          {/* Manual Reclassification */}
          <div className="panel-section">
            <span className="panel-section-label">Classify Impact</span>
            <p className="panel-classify-hint">
              Click to reclassify this article's oil price impact:
            </p>
            <div className="panel-classify-pills">
              {IMPACT_OPTIONS.map((opt) => (
                <button
                  key={opt}
                  className={`panel-classify-pill ${currentImpact === opt ? 'active' : ''}`}
                  style={{
                    '--pill-color': getImpactColor(opt),
                    '--pill-bg': getImpactBgColor(opt),
                  }}
                  onClick={() => handleReclassify(opt)}
                  disabled={saving}
                >
                  {getImpactEmoji(opt)} {opt}
                </button>
              ))}
            </div>
            {saving && <span className="panel-classify-saving">Saving…</span>}
          </div>

          {/* Confidence */}
          <div className="panel-section">
            <span className="panel-section-label">Confidence</span>
            <div className="panel-confidence-bar">
              <div
                className="panel-confidence-fill"
                style={{
                  width: `${confidencePct}%`,
                  background: impactColor,
                }}
              />
            </div>
            <span className="panel-confidence-text">{confidencePct}%</span>
          </div>

          {/* Importance Score */}
          <div className="panel-section">
            <span className="panel-section-label">Importance</span>
            <div className="panel-importance">
              <span
                className="panel-importance-value"
                style={{ color: impactColor }}
              >
                {typeof importance === 'number' ? importance.toFixed(1) : importance}
              </span>
              <span className="panel-importance-label">/ 100</span>
            </div>
          </div>

          {/* Event Type */}
          {(article.event_type || article.type) && (
            <div className="panel-section">
              <span className="panel-section-label">Event Type</span>
              <span className="panel-event-badge">
                {article.event_type || article.type}
              </span>
            </div>
          )}

          {/* Entities */}
          {article.entities && article.entities.length > 0 && (
            <div className="panel-section">
              <span className="panel-section-label">Key Entities</span>
              <div className="panel-entities">
                {article.entities.map((entity, i) => (
                  <span key={i} className="panel-entity-badge">{entity}</span>
                ))}
              </div>
            </div>
          )}

          {/* Location */}
          {article.location && (
            <div className="panel-section">
              <span className="panel-section-label">Location</span>
              <span className="panel-location-badge">📍 {article.location}</span>
            </div>
          )}

          {/* Description */}
          {(article.description || article.summary) && (
            <div className="panel-section">
              <span className="panel-section-label">Description</span>
              <p className="panel-description">
                {article.description || article.summary}
              </p>
            </div>
          )}

          {/* Link */}
          {article.url && (
            <a
              className="panel-link"
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Read Full Article →
            </a>
          )}
        </div>
      </aside>
    </>
  );
});

export default ArticlePanel;

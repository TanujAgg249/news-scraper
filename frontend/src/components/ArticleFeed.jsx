import React, { memo, useCallback } from 'react';
import {
  getImpactColor,
  getImpactEmoji,
  getImpactBgColor,
  getImpactLabel,
} from '../utils/colors';
import './ArticleFeed.css';

const IMPACT_FILTERS = [
  { id: 'All', label: 'All' },
  { id: 'Bullish', label: 'Bullish', title: 'Puts upward pressure on oil prices' },
  { id: 'Bearish', label: 'Bearish', title: 'Puts downward pressure on oil prices' },
  { id: 'Mixed', label: 'Mixed', title: 'Contains both bullish and bearish signals' },
  { id: 'Neutral', label: 'Neutral', title: 'No expected impact on oil prices' },
];

function timeAgo(dateStr) {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHrs = Math.floor(diffMins / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffHrs / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
}

function isLiveArticle(dateStr) {
  if (!dateStr) return false;
  try {
    const diffMs = Date.now() - new Date(dateStr).getTime();
    return diffMs < 60 * 60 * 1000; // less than 1 hour old
  } catch {
    return false;
  }
}

const ArticleFeedCard = memo(function ArticleFeedCard({
  article,
  isSelected,
  isNew,
  onClick,
}) {
  const impact = article.oil_impact || article.impact || 'Unknown';
  const impactColor = getImpactColor(impact);
  const live = isLiveArticle(article.published_at);

  return (
    <div
      className={`feed-card ${isSelected ? 'selected' : ''} ${isNew ? 'new-article' : ''}`}
      style={{
        borderLeftColor: isNew ? '#FFD700' : impactColor,
      }}
      onClick={() => onClick(article)}
    >
      <div className="feed-card-headline">
        {isNew && <span className="feed-new-badge">NEW</span>}
        {live && !isNew && <span className="feed-live-badge">🔴 LIVE</span>}
        {article.headline || article.title || 'Untitled'}
      </div>
      <div className="feed-card-meta">
        <span className="feed-card-source">
          {article.source || 'Unknown'}
        </span>
        <span className="feed-card-sep" />
        <span>{timeAgo(article.published_at)}</span>
        <span
          className="feed-card-badge"
          style={{
            color: impactColor,
            background: getImpactBgColor(impact),
          }}
        >
          {getImpactEmoji(impact)} {getImpactLabel(impact)}
        </span>
      </div>
    </div>
  );
});

const ArticleFeed = memo(function ArticleFeed({
  articles,
  loading,
  onArticleClick,
  selectedArticleId,
  search,
  onSearchChange,
  impactFilter,
  onImpactFilterChange,
  newNodeIds,
}) {
  const handleSearch = useCallback((e) => {
    onSearchChange(e.target.value);
  }, [onSearchChange]);

  const newSet = newNodeIds || new Set();

  return (
    <div className="article-feed">
      {/* Search */}
      <div className="feed-search">
        <div className="feed-search-wrap">
          <span className="feed-search-icon">🔍</span>
          <input
            className="feed-search-input"
            type="text"
            placeholder="Search articles…"
            value={search}
            onChange={handleSearch}
          />
        </div>
      </div>

      {/* Impact Filters */}
      <div className="feed-filter-section">
        <span className="feed-filter-label">Oil Price Impact</span>
        <div className="feed-filters">
          {IMPACT_FILTERS.map((f) => (
            <button
              key={f.id}
              className={`feed-filter-pill ${impactFilter === f.id ? 'active' : ''}`}
              onClick={() => onImpactFilterChange(f.id)}
              title={f.title || 'Show all articles'}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Article List */}
      <div className="feed-list">
        {loading && articles.length === 0 ? (
          <div className="feed-loading">
            <div className="feed-loading-spinner" />
          </div>
        ) : articles.length === 0 ? (
          <div className="feed-empty">
            <span className="feed-empty-icon">📭</span>
            <span className="feed-empty-text">No articles found</span>
          </div>
        ) : (
          <>
            {articles.map((article, index) => (
              <ArticleFeedCard
                key={article.id || index}
                article={article}
                isSelected={selectedArticleId && article.id === selectedArticleId}
                isNew={newSet.has(article.id)}
                onClick={onArticleClick}
              />
            ))}
          </>
        )}
      </div>
    </div>
  );
});

export default ArticleFeed;

import React, { useState, useCallback, useEffect, useMemo, Suspense, lazy, useRef } from 'react';
import Header from './components/Header';
import NewsGraph3D from './components/NewsGraph3D';
import ArticlePanel from './components/ArticlePanel';
import ArticleFeed from './components/ArticleFeed';
import OilPriceWidget from './components/OilPriceWidget';
import TopicManager from './components/TopicManager';
import { useGraphData } from './hooks/useGraphData';
import { useArticles } from './hooks/useArticles';
import { fetchTopics } from './api/client';
import './App.css';

const WorldMap = lazy(() => import('./components/WorldMap'));

function App() {
  // State
  const [activeTopic, setActiveTopic] = useState(null);
  const [topics, setTopics] = useState([]);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [showTopicManager, setShowTopicManager] = useState(false);
  const [viewMode, setViewMode] = useState('graph');

  // Lifted search/filter state
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [impactFilter, setImpactFilter] = useState('All');
  const [timelineValue, setTimelineValue] = useState(100); // 0 to 100
  const searchTimerRef = useRef(null);

  // Debounce search
  useEffect(() => {
    searchTimerRef.current = setTimeout(() => {
      setDebouncedSearch(search);
    }, 300);
    return () => clearTimeout(searchTimerRef.current);
  }, [search]);

  // Build filters for articles hook
  const articleFilters = useMemo(
    () => ({
      topic_id: activeTopic || undefined,
      search: debouncedSearch || undefined,
      oil_impact: impactFilter !== 'All' ? impactFilter : undefined,
    }),
    [activeTopic, debouncedSearch, impactFilter]
  );

  // Data hooks
  const {
    graphData,
    loading: graphLoading,
    error: graphError,
    refetch: refetchGraph,
  } = useGraphData(activeTopic);

  const {
    articles,
    loading: articlesLoading,
    hasMore,
    loadMore,
  } = useArticles(articleFilters);

  // Derive Min and Max times for the timeline slider
  const { minTime, maxTime } = useMemo(() => {
    if (!graphData?.nodes?.length) return { minTime: Date.now(), maxTime: Date.now() };
    const times = graphData.nodes.map(n => new Date(n.published_at).getTime()).filter(t => !isNaN(t));
    return { minTime: Math.min(...times), maxTime: Math.max(...times) };
  }, [graphData]);

  // Filter graphData by timeline
  const filteredGraphData = useMemo(() => {
    if (timelineValue === 100 || !graphData?.nodes?.length) return graphData;
    const cutoffTime = minTime + (maxTime - minTime) * (timelineValue / 100);
    const filteredNodes = graphData.nodes.filter(n => new Date(n.published_at).getTime() <= cutoffTime);
    const kept = new Set(filteredNodes.map(n => n.id));
    const filteredLinks = graphData.links.filter(l => {
      const s = typeof l.source === 'object' ? l.source.id : l.source;
      const t = typeof l.target === 'object' ? l.target.id : l.target;
      return kept.has(s) && kept.has(t);
    });
    return { nodes: filteredNodes, links: filteredLinks };
  }, [graphData, minTime, maxTime, timelineValue]);

  // Load topics
  const loadTopics = useCallback(async () => {
    try {
      const data = await fetchTopics();
      const list = Array.isArray(data) ? data : data.topics || [];
      setTopics(list);
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    loadTopics();
  }, [loadTopics]);

  // Handlers
  const handleTopicChange = useCallback((topicName) => {
    setActiveTopic(topicName);
  }, []);

  const handleNodeClick = useCallback((node) => {
    setSelectedArticle(node);
  }, []);

  const handleArticleClick = useCallback((article) => {
    setSelectedArticle(article);
  }, []);

  const handleClosePanel = useCallback(() => {
    setSelectedArticle(null);
  }, []);

  const handleOpenTopicManager = useCallback(() => {
    setShowTopicManager(true);
  }, []);

  const handleCloseTopicManager = useCallback(() => {
    setShowTopicManager(false);
  }, []);

  const handleTopicsChange = useCallback(() => {
    loadTopics();
    refetchGraph();
  }, [loadTopics, refetchGraph]);

  const handleSearchChange = useCallback((value) => {
    setSearch(value);
  }, []);

  const handleImpactFilterChange = useCallback((value) => {
    setImpactFilter(value);
  }, []);

  // Derive last updated time
  const lastUpdated = useMemo(() => {
    return new Date().toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  }, [articles]);

  const sentimentCounts = useMemo(() => {
    const counts = { positive: 0, negative: 0, neutral: 0 };
    const nodes = filteredGraphData?.nodes || [];
    nodes.forEach(art => {
      const impact = art.oil_impact?.toLowerCase() || '';
      if (impact === 'positive') counts.positive++;
      else if (impact === 'negative') counts.negative++;
      else if (impact === 'neutral') counts.neutral++;
    });
    return counts;
  }, [filteredGraphData]);

  const activeTopicObj = useMemo(() => {
    return topics.find(t => t.id === activeTopic);
  }, [topics, activeTopic]);

  const timelineCutoffDate = new Date(minTime + (maxTime - minTime) * (timelineValue / 100));

  return (
    <div className="app">
      {/* Header */}
      <Header
        topics={topics}
        activeTopic={activeTopic}
        onTopicChange={handleTopicChange}
        onManageTopics={handleOpenTopicManager}
      />

      {/* Main Content */}
      <main className="app-main">
        {/* 3D Graph / Globe */}
        <section className="app-graph">
          {/* View Toggle */}
          <div className="view-toggle">
            <button
              className={`view-toggle-btn ${viewMode === 'graph' ? 'active' : ''}`}
              onClick={() => setViewMode('graph')}
            >
              🔗 Graph
            </button>
            <button
            className={`view-toggle-btn ${viewMode === 'map' ? 'active' : ''}`}
            onClick={() => setViewMode('map')}
          >
            🗺️ Map
          </button>
          </div>

          {viewMode === 'graph' ? (
            <NewsGraph3D
              graphData={filteredGraphData}
              onNodeClick={handleNodeClick}
              selectedNodeId={selectedArticle?.id}
            />
          ) : (
            <Suspense
              fallback={
                <div className="graph-container">
                  <div className="graph-loading">
                    <div className="graph-spinner" />
                    <span className="graph-loading-text">Loading map…</span>
                  </div>
                </div>
              }
            >
              <WorldMap
                graphData={filteredGraphData}
                onNodeClick={handleNodeClick}
                selectedNodeId={selectedArticle?.id}
                loading={graphLoading}
                error={graphError}
                onRetry={refetchGraph}
              />
            </Suspense>
          )}

          {/* AI Executive Briefing */}
          {activeTopicObj?.macro_summary && (
            <div className="macro-summary-panel">
              <h3>🧠 AI Executive Briefing</h3>
              <ul>
                {activeTopicObj.macro_summary.split('\n').map(l => l.replace(/^[-*]\s*/, '')).filter(l => l.trim()).map((bullet, i) => (
                  <li key={i}>{bullet}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Timeline Slider */}
          {graphData?.nodes?.length > 0 && (
            <div className="timeline-slider-container">
              <span className="timeline-label">Time-Lapse</span>
              <input
                type="range"
                min="0"
                max="100"
                value={timelineValue}
                onChange={(e) => setTimelineValue(Number(e.target.value))}
                className="timeline-slider"
              />
              <span className="timeline-label">
                {timelineValue === 100 ? 'Live' : timelineCutoffDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          )}
        </section>

        {/* Sidebar */}
        <aside className="app-sidebar">
          <OilPriceWidget />
          <ArticleFeed
            articles={articles}
            loading={articlesLoading}
            hasMore={hasMore}
            onLoadMore={loadMore}
            onArticleClick={handleArticleClick}
            selectedArticleId={selectedArticle?.id}
            search={search}
            onSearchChange={handleSearchChange}
            impactFilter={impactFilter}
            onImpactFilterChange={handleImpactFilterChange}
          />
        </aside>
      </main>

      {/* Status Bar */}
      <footer className="app-status">
        <span className="app-status-item">
          {filteredGraphData?.nodes?.length || 0} nodes
        </span>
        <span className="app-status-sep">•</span>
        <span className="app-status-item" style={{ color: 'var(--bullish)' }}>
          {sentimentCounts.positive} 🟢 Positive
        </span>
        <span className="app-status-sep">•</span>
        <span className="app-status-item" style={{ color: 'var(--bearish)' }}>
          {sentimentCounts.negative} 🔴 Negative
        </span>
        <span className="app-status-sep">•</span>
        <span className="app-status-item" style={{ color: 'var(--neutral)' }}>
          {sentimentCounts.neutral} 🟡 Neutral
        </span>
        <span className="app-status-sep" />
        <span className="app-status-item">
          Updated {lastUpdated}
        </span>
        <span className="app-status-sep" />
        <span className="app-status-live">
          <span className="app-status-live-dot" />
          Live
        </span>
      </footer>

      {/* Article Detail Panel (overlay) */}
      {selectedArticle && (
        <ArticlePanel
          article={selectedArticle}
          onClose={handleClosePanel}
        />
      )}

      {/* Topic Manager Modal */}
      {showTopicManager && (
        <TopicManager
          onClose={handleCloseTopicManager}
          onTopicsChange={handleTopicsChange}
        />
      )}
    </div>
  );
}

export default App;

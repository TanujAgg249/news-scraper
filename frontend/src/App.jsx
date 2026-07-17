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
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [activeTopic, setActiveTopic] = useState(null);
  const [topics, setTopics] = useState([]);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [showTopicManager, setShowTopicManager] = useState(false);
  const [viewMode, setViewMode] = useState('graph');

  // Theme management
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  // Lifted search/filter state
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [impactFilter, setImpactFilter] = useState('All');

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

  // Handle reclassification: update graph node color + selected article
  const handleReclassify = useCallback((articleId, newImpact) => {
    // Update the selected article in state
    setSelectedArticle((prev) => {
      if (prev && prev.id === articleId) {
        return { ...prev, oil_impact: newImpact, impact: newImpact };
      }
      return prev;
    });
    // Trigger a graph refetch to update node colors
    refetchGraph();
  }, [refetchGraph]);

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

  const stats = useMemo(() => {
    let bullish = 0, bearish = 0, mixed = 0;
    (graphData?.nodes || []).forEach(n => {
      const i = n.oil_impact || n.impact;
      if (i === 'Bullish' || i === 'Positive') bullish++;
      if (i === 'Bearish' || i === 'Negative') bearish++;
      if (i === 'Mixed') mixed++;
    });
    return { bullish, bearish, mixed };
  }, [graphData]);

  const activeTopicObj = useMemo(() => {
    return topics.find(t => t.id === activeTopic);
  }, [topics, activeTopic]);

  // Check if user has no topics (for welcome state)
  const showWelcome = topics.length === 0 && (!graphData?.nodes?.length);

  return (
    <div className="app">
      {/* Header */}
      <Header
        topics={topics}
        activeTopic={activeTopic}
        onTopicChange={handleTopicChange}
        onManageTopics={handleOpenTopicManager}
        theme={theme}
        onThemeToggle={toggleTheme}
      />

      {/* Main Content */}
      <main className="app-main">
        {/* 3D Graph / Globe */}
        <section className="app-graph">
          {/* Welcome State for New Users */}
          {showWelcome && (
            <div className="welcome-state">
              <div className="welcome-icon">⚡</div>
              <h2 className="welcome-title">Welcome to EnergyPulse</h2>
              <p className="welcome-desc">
                Track energy news in real-time with AI-powered analysis.
                Add a topic to start monitoring articles, sentiment, and oil price impact.
              </p>
              <button className="welcome-cta" onClick={handleOpenTopicManager}>
                + Add Your First Topic
              </button>
            </div>
          )}

          {/* View Toggle */}
          {!showWelcome && (
            <div className="view-toggle">
              <button
                className={`view-toggle-btn ${viewMode === 'graph' ? 'active' : ''}`}
                onClick={() => setViewMode('graph')}
                title="Interactive 3D network showing how articles relate to each other"
              >
                🔗 Graph
              </button>
              <button
                className={`view-toggle-btn ${viewMode === 'map' ? 'active' : ''}`}
                onClick={() => setViewMode('map')}
                title="Geographic view showing where news events are happening"
              >
                🗺️ Map
              </button>
              <span className="view-toggle-hint">Click any node to read the article</span>
            </div>
          )}

          {viewMode === 'graph' ? (
            <NewsGraph3D
              graphData={graphData}
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
                graphData={graphData}
                onNodeClick={handleNodeClick}
                selectedNodeId={selectedArticle?.id}
                loading={graphLoading}
                error={graphError}
                onRetry={refetchGraph}
              />
            </Suspense>
          )}

          {/* AI Executive Briefing disabled per user request */}
          {/*
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
          */}


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
          {graphData?.nodes?.length || 0} nodes
        </span>
        <span className="app-status-sep">•</span>
              <span className="app-stat app-stat-bullish">
                🟢 {stats.bullish} Bullish
              </span>
              <span className="app-stat app-stat-bearish">
                🔴 {stats.bearish} Bearish
              </span>
              <span className="app-stat app-stat-mixed">
                🟣 {stats.mixed} Mixed
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
          onReclassify={handleReclassify}
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

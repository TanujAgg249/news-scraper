import React, { memo, useState, useEffect, useCallback } from 'react';
import {
  fetchTopics,
  createTopic,
  updateTopic,
  deleteTopic,
  scrapeTopic,
  API_BASE,
} from '../api/client';
import './TopicManager.css';

const TopicManager = memo(function TopicManager({ onClose, onTopicsChange }) {
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState('');
  const [scrapingId, setScrapingId] = useState(null);
  const [scrapeResult, setScrapeResult] = useState('');

  // Add topic form state
  const [name, setName] = useState('');
  const [query, setQuery] = useState('');
  const [keywords, setKeywords] = useState('');
  const [timeFilter, setTimeFilter] = useState('d');
  const [rssFeeds, setRssFeeds] = useState('');

  // Edit mode state
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [editQuery, setEditQuery] = useState('');
  const [editKeywords, setEditKeywords] = useState('');
  const [editRssFeeds, setEditRssFeeds] = useState('');
  const [editTimeFilter, setEditTimeFilter] = useState('d');
  const [editError, setEditError] = useState('');

  const loadTopics = useCallback(async () => {
    try {
      const data = await fetchTopics();
      const list = Array.isArray(data) ? data : data.topics || [];
      setTopics(list);
    } catch {
      // silently fail, user can retry
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTopics();
  }, [loadTopics]);

  // Escape key handler
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const handleEdit = useCallback((topic) => {
    setEditingId(topic.id);
    setEditName(topic.name || '');
    setEditQuery(topic.query || '');
    setEditKeywords((topic.keywords || []).join(', '));
    setEditTimeFilter(topic.time_filter || 'd');
    setEditRssFeeds((topic.rss_feeds || []).join(', '));
    setEditError('');
  }, []);

  const handleEditSave = useCallback(async () => {
    if (!editName.trim() || !editQuery.trim()) {
      setEditError('Name and query are required.');
      return;
    }
    try {
      const editedTopic = topics.find((t) => t.id === editingId);
      await updateTopic(editingId, {
        name: editName.trim(),
        query: editQuery.trim(),
        keywords: editKeywords.split(',').map((k) => k.trim()).filter(Boolean),
        time_filter: editTimeFilter,
        rss_feeds: editRssFeeds.split(',').map((u) => u.trim()).filter(Boolean),
        is_active: editedTopic ? editedTopic.is_active : true,
      });
      setEditingId(null);
      await loadTopics();
      if (onTopicsChange) onTopicsChange();
    } catch (err) {
      setEditError(err.message || 'Failed to update topic.');
    }
  }, [editingId, editName, editQuery, editKeywords, editRssFeeds, topics, loadTopics, onTopicsChange]);

  const handleEditCancel = useCallback(() => {
    setEditingId(null);
    setEditError('');
  }, []);

  const handleToggle = useCallback(async (topic) => {
    try {
      setActionError('');
      await updateTopic(topic.id, { is_active: !topic.is_active });
      await loadTopics();
      if (onTopicsChange) onTopicsChange();
    } catch (err) {
      setActionError(`Failed to toggle "${topic.name}": ${err.message}`);
    }
  }, [loadTopics, onTopicsChange]);

  const handleDelete = useCallback(async (topic) => {
    if (!window.confirm(`Delete topic "${topic.name}"? This will also delete all associated articles.`)) return;
    try {
      setActionError('');
      await deleteTopic(topic.id);
      await loadTopics();
      if (onTopicsChange) onTopicsChange();
    } catch (err) {
      setActionError(`Failed to delete "${topic.name}": ${err.message}`);
    }
  }, [loadTopics, onTopicsChange]);

  const handleScrape = useCallback(async (topic) => {
    try {
      setScrapingId(topic.id);
      setScrapeResult('');
      setActionError('');
      
      // Trigger the background scrape
      await scrapeTopic(topic.id);
      setScrapeResult(`Connecting to live feed for ${topic.name}...`);
      
      // Connect to SSE for live progress
      const evtSource = new EventSource(`${API_BASE}/topics/${topic.id}/scrape/status`);
      
      evtSource.onmessage = async (event) => {
        try {
          const data = JSON.parse(event.data);
          setScrapeResult(`${data.status}`);
          
          if (data.status.includes('Completed') || data.status.includes('Error')) {
            evtSource.close();
            setScrapingId(null);
            await loadTopics();
            if (onTopicsChange) onTopicsChange();
          }
        } catch (e) {
          // ignore parsing errors
        }
      };
      
      evtSource.onerror = () => {
        evtSource.close();
        setScrapingId(null);
        setScrapeResult(`Connection lost to live feed. Scrape may still be running.`);
        loadTopics();
      };

    } catch (err) {
      setActionError(`Scrape failed for "${topic.name}": ${err.message}`);
      setScrapingId(null);
    }
  }, [loadTopics, onTopicsChange]);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (!name.trim() || !query.trim()) {
      setFormError('Name and search query are required.');
      return;
    }
    setSubmitting(true);
    setFormError('');
    try {
      await createTopic({
        name: name.trim(),
        query: query.trim(),
        keywords: keywords.split(',').map((k) => k.trim()).filter(Boolean),
        time_filter: timeFilter,
        rss_feeds: rssFeeds.split(',').map((u) => u.trim()).filter(Boolean),
        is_active: true,
      });
      setName('');
      setQuery('');
      setKeywords('');
      setTimeFilter('d');
      setRssFeeds('');
      await loadTopics();
      if (onTopicsChange) onTopicsChange();
    } catch (err) {
      setFormError(err.message || 'Failed to create topic.');
    } finally {
      setSubmitting(false);
    }
  }, [name, query, keywords, rssFeeds, loadTopics, onTopicsChange]);

  return (
    <div className="topic-modal-backdrop" onClick={onClose}>
      <div className="topic-modal" onClick={(e) => e.stopPropagation()}>
        <div className="topic-modal-header">
          <h2 className="topic-modal-title">Manage Topics</h2>
          <button
            className="topic-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="topic-modal-body">
          {actionError && (
            <div className="topic-action-error">{actionError}</div>
          )}
          {scrapeResult && (
            <div className="topic-scrape-result">
              {scrapingId && <div className="topic-scrape-spinner" />}
              <div className="topic-scrape-text">{scrapeResult}</div>
            </div>
          )}

          {/* Topic List */}
          <div className="topic-list">
            {loading ? (
              <div className="topic-list-empty">Loading topics…</div>
            ) : topics.length === 0 ? (
              <div className="topic-list-empty">
                No topics configured. Add your first topic below.
              </div>
            ) : (
              topics.map((topic) => (
                <div key={topic.id || topic.name} className="topic-item">
                  {editingId === topic.id ? (
                    /* Edit Mode */
                    <div className="topic-item-edit-form">
                      <div className="topic-form-group">
                        <label className="topic-form-label">Name</label>
                        <input
                          className="topic-edit-input"
                          type="text"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          placeholder="Topic name"
                        />
                      </div>
                      <div className="topic-form-group">
                        <label className="topic-form-label">Search Query</label>
                        <input
                          className="topic-edit-input"
                          type="text"
                          value={editQuery}
                          onChange={(e) => setEditQuery(e.target.value)}
                          placeholder="Search query"
                        />
                      </div>
                      <div className="topic-form-group">
                        <label className="topic-form-label">Keywords (comma-separated)</label>
                        <input
                          className="topic-edit-input"
                          type="text"
                          value={editKeywords}
                          onChange={(e) => setEditKeywords(e.target.value)}
                          placeholder="keyword1, keyword2"
                        />
                      </div>
                      <div className="topic-form-group">
                        <label className="topic-form-label">Time Filter (Historical Fetching)</label>
                        <select
                          className="topic-edit-input"
                          value={editTimeFilter}
                          onChange={(e) => setEditTimeFilter(e.target.value)}
                        >
                          <option value="d">Past Day</option>
                          <option value="w">Past Week</option>
                          <option value="m">Past Month</option>
                        </select>
                      </div>
                      <div className="topic-form-group">
                        <label className="topic-form-label">RSS Feeds (comma-separated)</label>
                        <input
                          className="topic-edit-input"
                          type="text"
                          value={editRssFeeds}
                          onChange={(e) => setEditRssFeeds(e.target.value)}
                          placeholder="https://feed1.com, https://feed2.com"
                        />
                      </div>
                      {editError && (
                        <span className="topic-form-error">{editError}</span>
                      )}
                      <div className="topic-edit-actions">
                        <button
                          className="topic-edit-save"
                          onClick={handleEditSave}
                          type="button"
                        >
                          Save
                        </button>
                        <button
                          className="topic-edit-cancel"
                          onClick={handleEditCancel}
                          type="button"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* View Mode */
                    <>
                      <div
                        className={`topic-item-indicator ${
                          topic.is_active !== false ? 'active' : 'inactive'
                        }`}
                      />
                      <div className="topic-item-info">
                        <div className="topic-item-name">{topic.name}</div>
                        <div className="topic-item-query">
                          {topic.query || topic.search_query || '—'}
                        </div>
                        {topic.keywords && topic.keywords.length > 0 && (
                          <div className="topic-item-keywords">
                            {topic.keywords.map((kw, i) => (
                              <span key={i} className="topic-keyword-chip">
                                {kw}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="topic-item-actions">
                        <button
                          className="topic-item-btn scrape"
                          onClick={() => handleScrape(topic)}
                          disabled={scrapingId === topic.id}
                          title="Trigger manual scrape"
                        >
                          {scrapingId === topic.id ? '⏳' : '🔄'}
                          {scrapingId === topic.id ? ' Scraping...' : ' Scrape Now'}
                        </button>
                        <button
                          className="topic-item-btn edit"
                          onClick={() => handleEdit(topic)}
                        >
                          ✏️
                        </button>
                        <button
                          className="topic-item-btn toggle"
                          onClick={() => handleToggle(topic)}
                        >
                          {topic.is_active !== false ? 'Disable' : 'Enable'}
                        </button>
                        <button
                          className="topic-item-btn delete"
                          onClick={() => handleDelete(topic)}
                        >
                          Delete
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Add Topic Form */}
          <form className="topic-form" onSubmit={handleSubmit}>
            <span className="topic-form-title">Add New Topic</span>

            <div className="topic-form-group">
              <label className="topic-form-label">Name</label>
              <input
                className="topic-form-input"
                type="text"
                placeholder="e.g., OPEC Policy"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="topic-form-group">
              <label className="topic-form-label">Search Query</label>
              <input
                className="topic-form-input"
                type="text"
                placeholder="e.g., OPEC production cuts oil supply"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>

            <div className="topic-form-group">
              <label className="topic-form-label">
                Keywords (comma-separated)
              </label>
              <input
                className="topic-form-input"
                type="text"
                placeholder="e.g., OPEC, oil production, supply cuts"
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
              />
            </div>

            <div className="topic-form-group">
              <label className="topic-form-label">Time Filter (Historical Fetching)</label>
              <select
                className="topic-form-input"
                value={timeFilter}
                onChange={(e) => setTimeFilter(e.target.value)}
              >
                <option value="d">Past Day</option>
                <option value="w">Past Week</option>
                <option value="m">Past Month</option>
              </select>
            </div>

            <div className="topic-form-group">
              <label className="topic-form-label">
                RSS Feeds (comma-separated URLs, optional)
              </label>
              <input
                className="topic-form-input"
                type="text"
                placeholder="e.g., https://feeds.reuters.com/energy"
                value={rssFeeds}
                onChange={(e) => setRssFeeds(e.target.value)}
              />
            </div>

            {formError && (
              <span className="topic-form-error">{formError}</span>
            )}

            <button
              className="topic-form-submit"
              type="submit"
              disabled={submitting}
            >
              {submitting ? 'Creating…' : 'Add Topic'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
});

export default TopicManager;

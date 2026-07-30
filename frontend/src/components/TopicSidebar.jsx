import React, { memo, useState, useMemo, useCallback } from 'react';
import './TopicSidebar.css';

const TopicSidebar = memo(function TopicSidebar({
  topics,
  activeTopic,
  onTopicChange,
  onManageTopics,
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [search, setSearch] = useState('');

  const toggleCollapse = useCallback(() => {
    setCollapsed(prev => !prev);
  }, []);

  const handleTopicClick = useCallback(
    (topicId) => {
      if (activeTopic === topicId) {
        onTopicChange(null);
      } else {
        onTopicChange(topicId);
      }
    },
    [activeTopic, onTopicChange]
  );

  const filteredTopics = useMemo(() => {
    if (!search.trim()) return topics;
    const q = search.toLowerCase();
    return topics.filter(t => t.name.toLowerCase().includes(q));
  }, [topics, search]);

  return (
    <aside className={`topic-sidebar ${collapsed ? 'collapsed' : ''}`}>
      {/* Header with title + collapse toggle */}
      <div className="topic-sidebar-header">
        <span className="topic-sidebar-title">Topics</span>
        <button
          className="topic-sidebar-toggle"
          onClick={toggleCollapse}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
      </div>

      {/* Search */}
      <div className="topic-sidebar-search">
        <div className="topic-sidebar-search-wrap">
          <svg
            className="topic-sidebar-search-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            className="topic-sidebar-search-input"
            type="text"
            placeholder="Search topics…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Topic list */}
      <div className="topic-sidebar-list">
        {/* "All" button */}
        <button
          className={`topic-sidebar-item ${activeTopic === null ? 'active' : ''}`}
          onClick={() => onTopicChange(null)}
          title={collapsed ? 'All' : undefined}
        >
          <span className="topic-sidebar-item-dot" />
          <span className="topic-sidebar-item-label">All</span>
        </button>

        {filteredTopics.map(topic => (
          <button
            key={topic.id}
            className={`topic-sidebar-item ${activeTopic === topic.id ? 'active' : ''}`}
            onClick={() => handleTopicClick(topic.id)}
            title={collapsed ? topic.name : undefined}
          >
            <span className="topic-sidebar-item-dot" />
            <span className="topic-sidebar-item-label">{topic.name}</span>
          </button>
        ))}

        {filteredTopics.length === 0 && search.trim() && (
          <div className="topic-sidebar-empty">
            No topics match "{search}"
          </div>
        )}
      </div>

      {/* Manage topics button */}
      <div className="topic-sidebar-manage">
        <button
          className="topic-sidebar-manage-btn"
          onClick={onManageTopics}
          title={collapsed ? 'Manage Topics' : undefined}
        >
          <span className="topic-sidebar-manage-icon">⚙</span>
          <span className="topic-sidebar-manage-label">Manage Topics</span>
        </button>
      </div>
    </aside>
  );
});

export default TopicSidebar;

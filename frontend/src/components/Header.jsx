import React, { memo, useCallback } from 'react';
import './Header.css';

const Header = memo(function Header({
  topics,
  activeTopic,
  onTopicChange,
  onManageTopics,
}) {
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

  return (
    <header className="header">
      <div className="header-left">
        <div className="header-logo">
          <div className="header-logo-icon">⚡</div>
          <h1 className="header-title">EnergyPulse</h1>
        </div>
      </div>

      <nav className="header-center">
        <button
          className={`topic-pill ${activeTopic === null ? 'active' : ''}`}
          onClick={() => onTopicChange(null)}
        >
          <span className="topic-pill-dot" />
          All
        </button>
        {topics.map((topic) => (
          <button
            key={topic.id}
            className={`topic-pill ${activeTopic === topic.id ? 'active' : ''}`}
            onClick={() => handleTopicClick(topic.id)}
          >
            <span className="topic-pill-dot" />
            {topic.name}
          </button>
        ))}
      </nav>

      <div className="header-right">
        <button className="header-btn" onClick={onManageTopics}>
          <span className="header-btn-icon">⚙</span>
          Manage Topics
        </button>
      </div>
    </header>
  );
});

export default Header;

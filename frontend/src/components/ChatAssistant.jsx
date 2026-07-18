import React, { useState, useRef, useEffect } from 'react';
import { askQuestion } from '../api/client';
import { getImpactColor } from '../utils/colors';
import './ChatAssistant.css';

export default function ChatAssistant({ isOpen, onClose }) {
  const [query, setQuery] = useState('');
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history, isLoading]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) return;

    // Add user message to history
    const newHistory = [...history, { role: 'user', content: trimmedQuery }];
    setHistory(newHistory);
    setQuery('');
    setIsLoading(true);

    try {
      const response = await askQuestion(trimmedQuery);
      setHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
        },
      ]);
    } catch (err) {
      setHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error while searching the database.',
          isError: true,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-assistant-overlay">
      <div className="chat-assistant-panel">
        <div className="chat-header">
          <div className="chat-header-title">
            EnergyPulseAI
          </div>
          <button className="chat-close-btn" onClick={onClose} title="Close Assistant">
            ✕
          </button>
        </div>

        <div className="chat-messages">
          {history.length === 0 && (
            <div className="chat-empty-state">
              <p>Ask a question about the oil market.</p>
              <div className="chat-suggestions">
                <button onClick={() => setQuery("What is the latest on Russian sanctions?")}>What is the latest on Russian sanctions?</button>
                <button onClick={() => setQuery("Are there any supply disruptions in the Middle East?")}>Are there any supply disruptions in the Middle East?</button>
              </div>
            </div>
          )}

          {history.map((msg, idx) => (
            <div key={idx} className={`chat-message ${msg.role}`}>
              <div className="chat-bubble">
                {msg.content.split('\n').map((line, i) => (
                  <p key={i}>{line}</p>
                ))}
              </div>
              
              {msg.sources && msg.sources.length > 0 && (
                <div className="chat-sources">
                  <div className="chat-sources-title">Sources:</div>
                  <div className="chat-source-list">
                    {msg.sources.map((src, i) => (
                      <a
                        key={i}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="chat-source-chip"
                        style={{ borderLeftColor: getImpactColor(src.oil_impact) }}
                      >
                        <span className="source-index">[{i + 1}]</span>
                        <span className="source-headline">{src.headline}</span>
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="chat-message assistant">
              <div className="chat-bubble loading-bubble">
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form className="chat-input-area" onSubmit={handleSubmit}>
          <input
            type="text"
            className="chat-input"
            placeholder="Ask about geopolitical events..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isLoading}
          />
          <button type="submit" className="chat-submit-btn" disabled={isLoading || !query.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

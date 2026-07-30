import { useState, useEffect, useCallback, useRef, useMemo } from 'react';

const NEW_NODE_GLOW_DURATION = 5 * 60 * 1000; // 5 minutes
import { fetchGraphData } from '../api/client';

const REFETCH_INTERVAL = 5 * 60 * 1000; // 5 minutes

export function useGraphData(activeTopic, timeFilter, hoursOverride) {
  const [rawData, setRawData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const params = {};
      if (activeTopic) {
        params.topic_id = activeTopic;
      }

      // hoursOverride from the time-range selector takes priority
      if (hoursOverride != null) {
        params.hours = hoursOverride;
      } else if (activeTopic) {
        if (timeFilter === 'h') {
          params.hours = 2; // 2 hour window for 'past hour' to account for slight timezone/publish delays
        } else if (timeFilter === 'd') {
          params.hours = 24;
        } else if (timeFilter === 'w') {
          params.hours = 168; // 7 * 24
        } else if (timeFilter === 'm') {
          params.hours = 720; // 30 * 24
        } else {
          params.hours = 48; // fallback
        }
      } else {
        params.hours = 24; // Keep time limit for global graph to prevent clutter
      }
      const data = await fetchGraphData(params);
      setRawData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [activeTopic, timeFilter, hoursOverride]);

  useEffect(() => {
    setLoading(true);
    fetchData();

    intervalRef.current = setInterval(fetchData, REFETCH_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchData]);

  const graphData = useMemo(() => {
    if (!rawData) return { nodes: [], links: [] };

    let nodes = rawData.nodes || [];
    let links = rawData.links || [];

    // Limit to 500 nodes for performance
    if (nodes.length > 500) {
      const sorted = [...nodes].sort(
        (a, b) => (b.importance_score || 0) - (a.importance_score || 0)
      );
      const kept = new Set(sorted.slice(0, 500).map((n) => n.id));
      nodes = sorted.slice(0, 500);
      links = links.filter((l) => {
        const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
        const targetId = typeof l.target === 'object' ? l.target.id : l.target;
        return kept.has(sourceId) && kept.has(targetId);
      });
    }

    return { nodes, links };
  }, [rawData]);

  // Notifications + new node tracking
  const seenNodesRef = useRef(new Set());
  const isInitialLoad = useRef(true);
  const [newNodeIds, setNewNodeIds] = useState(new Set());
  const glowTimerRef = useRef(null);

  // Reset tracking when topic changes — prevents false "NEW" flags
  useEffect(() => {
    isInitialLoad.current = true;
    setNewNodeIds(new Set());
    if (glowTimerRef.current) clearTimeout(glowTimerRef.current);
  }, [activeTopic]);

  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  useEffect(() => {
    if (!rawData?.nodes) return;
    
    if (isInitialLoad.current) {
      rawData.nodes.forEach(n => seenNodesRef.current.add(n.id));
      isInitialLoad.current = false;
      return;
    }

    const freshIds = [];
    let alerted = false;
    rawData.nodes.forEach(n => {
      if (!seenNodesRef.current.has(n.id)) {
        seenNodesRef.current.add(n.id);
        freshIds.push(n.id);
        if (n.importance_score >= 85 && 'Notification' in window && Notification.permission === 'granted') {
          if (!alerted) {
            new Notification('🚨 BREAKING EVENT', { body: n.headline });
            alerted = true;
          }
        }
      }
    });

    if (freshIds.length > 0) {
      setNewNodeIds(prev => {
        const updated = new Set(prev);
        freshIds.forEach(id => updated.add(id));
        return updated;
      });

      // Auto-clear glow after 5 minutes
      if (glowTimerRef.current) clearTimeout(glowTimerRef.current);
      glowTimerRef.current = setTimeout(() => {
        setNewNodeIds(new Set());
      }, NEW_NODE_GLOW_DURATION);
    }
  }, [rawData]);

  // Cleanup glow timer on unmount
  useEffect(() => {
    return () => {
      if (glowTimerRef.current) clearTimeout(glowTimerRef.current);
    };
  }, []);

  const refetch = useCallback(() => {
    setLoading(true);
    fetchData();
  }, [fetchData]);

  return { graphData, loading, error, refetch, newNodeIds };
}

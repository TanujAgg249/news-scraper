import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { fetchGraphData } from '../api/client';

const REFETCH_INTERVAL = 5 * 60 * 1000; // 5 minutes

export function useGraphData(activeTopic) {
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
      const data = await fetchGraphData(params);
      setRawData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [activeTopic]);

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

    // Limit to 300 nodes for performance
    if (nodes.length > 300) {
      const sorted = [...nodes].sort(
        (a, b) => (b.importance_score || 0) - (a.importance_score || 0)
      );
      const kept = new Set(sorted.slice(0, 300).map((n) => n.id));
      nodes = sorted.slice(0, 300);
      links = links.filter((l) => {
        const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
        const targetId = typeof l.target === 'object' ? l.target.id : l.target;
        return kept.has(sourceId) && kept.has(targetId);
      });
    }

    return { nodes, links };
  }, [rawData]);

  // Notifications logic
  const seenNodesRef = useRef(new Set());
  const isInitialLoad = useRef(true);

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

    let alerted = false;
    rawData.nodes.forEach(n => {
      if (!seenNodesRef.current.has(n.id)) {
        seenNodesRef.current.add(n.id);
        if (n.importance_score >= 85 && 'Notification' in window && Notification.permission === 'granted') {
          if (!alerted) {
            new Notification('🚨 BREAKING EVENT', { body: n.headline });
            alerted = true; // prevent spamming multiple notifications at once
          }
        }
      }
    });
  }, [rawData]);

  const refetch = useCallback(() => {
    setLoading(true);
    fetchData();
  }, [fetchData]);

  return { graphData, loading, error, refetch };
}

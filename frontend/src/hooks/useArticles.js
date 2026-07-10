import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchArticles } from '../api/client';

const REFETCH_INTERVAL = 5 * 60 * 1000; // 5 minutes
const PAGE_SIZE = 20;

export function useArticles(filters = {}) {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);
  const intervalRef = useRef(null);
  const filtersRef = useRef(filters);

  // Track filter changes
  if (
    JSON.stringify(filtersRef.current) !== JSON.stringify(filters)
  ) {
    filtersRef.current = filters;
  }

  const fetchData = useCallback(
    async (currentOffset = 0, append = false) => {
      try {
        setError(null);
        if (!append) setLoading(true);

        const f = filtersRef.current;
        const params = {
          limit: PAGE_SIZE,
          offset: currentOffset,
          topic_id: f.topic_id,
          search: f.search,
          oil_impact: f.oil_impact,
        };

        const data = await fetchArticles(params);
        const newArticles = Array.isArray(data)
          ? data
          : data.articles || data.items || [];

        if (append) {
          setArticles((prev) => [...prev, ...newArticles]);
        } else {
          setArticles(newArticles);
        }

        setHasMore(newArticles.length >= PAGE_SIZE);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Reset and re-fetch when filters change
  useEffect(() => {
    setOffset(0);
    setArticles([]);
    fetchData(0, false);

    intervalRef.current = setInterval(() => {
      fetchData(0, false);
    }, REFETCH_INTERVAL);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [filters.topic_id, filters.oil_impact, filters.search, fetchData]);

  const loadMore = useCallback(() => {
    const newOffset = offset + PAGE_SIZE;
    setOffset(newOffset);
    fetchData(newOffset, true);
  }, [offset, fetchData]);

  const refetch = useCallback(() => {
    setOffset(0);
    setArticles([]);
    fetchData(0, false);
  }, [fetchData]);

  return { articles, loading, error, refetch, hasMore, loadMore };
}

import { useState, useEffect, useRef, useCallback } from 'react';

interface UseInfiniteScrollOptions<T> {
  fetchData: (skip: number, limit: number) => Promise<{ items: T[]; hasMore: boolean }>;
  limit?: number;
}

export function useInfiniteScroll<T>({ fetchData, limit = 10 }: UseInfiniteScrollOptions<T>) {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const skipRef = useRef(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;

    setLoading(true);
    setError(null);

    try {
      const { items: newItems, hasMore: more } = await fetchData(skipRef.current, limit);
      setItems((prev) => (skipRef.current === 0 ? newItems : [...newItems, ...prev]));
      setHasMore(more);
      skipRef.current += limit;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [fetchData, limit, loading, hasMore]);

  useEffect(() => {
    loadMore();
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      if (container.scrollTop === 0 && !loading && hasMore) {
        const prevHeight = container.scrollHeight;
        loadMore().then(() => {
          const newHeight = container.scrollHeight;
          container.scrollTop = newHeight - prevHeight;
        });
      }
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, [loadMore, loading, hasMore]);

  const reset = useCallback(() => {
    setItems([]);
    setHasMore(true);
    skipRef.current = 0;
    loadMore();
  }, [loadMore]);

  const addItem = useCallback((item: T) => {
    setItems((prev) => [item, ...prev]);
  }, []);

  return { items, loading, hasMore, error, containerRef, loadMore, reset, addItem };
}

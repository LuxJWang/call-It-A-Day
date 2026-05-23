import { useState } from 'react';
import { useInfiniteScroll } from '../hooks/useInfiniteScroll';

const API_URL = 'http://localhost:8080';

interface DiaryEntry {
  id: number;
  content: string;
  created_at: string;
}

function DiarySection() {
  const [newEntry, setNewEntry] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const { items, loading, hasMore, containerRef, addItem, loadMore } = useInfiniteScroll<DiaryEntry>({
    fetchData: async (skip, limit) => {
      const response = await fetch(`${API_URL}/api/diaries?skip=${skip}&limit=${limit}`);
      if (!response.ok) throw new Error('Failed to fetch diary entries');
      const data = await response.json();
      return { items: data.entries, hasMore: data.has_more };
    },
    limit: 10,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEntry.trim() || submitting) return;

    setSubmitting(true);
    try {
      const response = await fetch(`${API_URL}/api/diaries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newEntry }),
      });
      if (!response.ok) throw new Error('Failed to create entry');
      const entry = await response.json();
      addItem(entry);
      setNewEntry('');
    } catch (err) {
      alert('Failed to save diary entry');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="section">
      <div className="section-header">Diary History</div>

      <div className="history-container" ref={containerRef}>
        {hasMore && (
          <div className="load-more">
            <button className="load-more-btn" onClick={loadMore} disabled={loading}>
              {loading ? 'Loading...' : 'Load more'}
            </button>
          </div>
        )}

        {items.length === 0 && !loading && (
          <div className="empty-state">No diary entries yet. Write your first one below!</div>
        )}

        {items.map((entry) => (
          <div key={entry.id} className="history-item">
            <div className="history-item-content">{entry.content}</div>
            <div className="history-item-date">{new Date(entry.created_at).toLocaleString()}</div>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="input-container">
        <textarea
          className="input-field"
          rows={3}
          placeholder="How was your day? Type here..."
          value={newEntry}
          onChange={(e) => setNewEntry(e.target.value)}
          disabled={submitting}
        />
        <button type="submit" className="submit-btn" disabled={submitting || !newEntry.trim()}>
          {submitting ? 'Saving...' : 'Submit'}
        </button>
      </form>
    </section>
  );
}

export default DiarySection;

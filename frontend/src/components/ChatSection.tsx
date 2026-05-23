import { useState, useRef, useEffect } from 'react';

const API_URL = 'http://localhost:8080';

interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

interface TraceEvent {
  id: number;
  layer?: string;
  node_name: string;
  event_type: string;
  tool_name?: string;
  input_json?: Record<string, unknown>;
  output_json?: Record<string, unknown>;
  latency_ms?: number;
  created_at: string;
}

function ChatSection() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [skip, setSkip] = useState(0);
  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([]);
  const [lastRunId, setLastRunId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchMessages = async (offset: number, limit: number = 20) => {
    const response = await fetch(`${API_URL}/api/chat?skip=${offset}&limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch messages');
    const data = await response.json();
    return { messages: data.messages, hasMore: data.has_more };
  };

  const loadMore = async () => {
    if (loading || !hasMore) return;
    setLoading(true);
    try {
      const { messages: newMessages, hasMore: more } = await fetchMessages(skip);
      setMessages((prev) => [...newMessages, ...prev]);
      setHasMore(more);
      setSkip((s) => s + 20);
    } catch (err) {
      console.error('Failed to load messages:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMore();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: newMessage,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setNewMessage('');
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage.content }),
      });

      if (!response.ok) throw new Error('Failed to get response');

      const data = await response.json();
      setTraceEvents(data.trace_events || []);
      setLastRunId(data.run_id || null);

      const assistantMessage: ChatMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      alert('Failed to get response');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="section">
      <div className="section-header">Chat</div>

      <div className="chat-messages" ref={containerRef}>
        {hasMore && (
          <div className="load-more">
            <button className="load-more-btn" onClick={loadMore} disabled={loading}>
              {loading ? 'Loading...' : 'Load more history'}
            </button>
          </div>
        )}

        {messages.length === 0 && !loading && (
          <div className="empty-state">Start a conversation about your day!</div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`chat-message ${msg.role}`}>
            {msg.content}
          </div>
        ))}

        {loading && (
          <div className="loading-indicator">Thinking...</div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {traceEvents.length > 0 && (
        <div className="trace-panel">
          <div className="trace-header">Tool Trace {lastRunId ? `· ${lastRunId.slice(0, 8)}` : ''}</div>
          {traceEvents.map((event) => (
            <details className="trace-event" key={event.id}>
              <summary>
                <span>{event.layer || 'system'}</span>
                <strong>{event.node_name}</strong>
                <span>{event.event_type}</span>
                {event.tool_name && <span>{event.tool_name}</span>}
                {event.latency_ms != null && <span>{event.latency_ms}ms</span>}
              </summary>
              <pre>{JSON.stringify({ input: event.input_json, output: event.output_json }, null, 2)}</pre>
            </details>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} className="input-container">
        <textarea
          className="input-field"
          rows={2}
          placeholder="Type your message..."
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          disabled={loading}
        />
        <button type="submit" className="submit-btn" disabled={loading || !newMessage.trim()}>
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </section>
  );
}

export default ChatSection;

import { useState, useEffect, useRef } from 'react';
import { authFetchJson } from '../api';

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

interface ChatSession {
  session_id: string;
  created_at: string;
  updated_at: string;
  expires_at: string;
  expired: boolean;
}

function ChatSection() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [selectedSessionLoading, setSelectedSessionLoading] = useState(false);
  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([]);
  const [lastRunId, setLastRunId] = useState<string | null>(null);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadSessions = async () => {
    try {
      const data = await authFetchJson('/chat/sessions');
      setSessions(data || []);
      const activeSession = (data || []).find((session: ChatSession) => !session.expired);
      if (activeSession) {
        await loadSession(activeSession.session_id);
      }
    } catch (err) {
      console.error('Failed to load chat sessions:', err);
    }
  };

  const loadSession = async (sessionId: string) => {
    setSelectedSessionLoading(true);
    setCurrentSessionId(sessionId);
    setMessages([]);
    setSkip(0);
    setHasMore(true);
    setTraceEvents([]);
    setLastRunId(null);

    try {
      const data = await authFetchJson(`/chat?session_id=${sessionId}&skip=0&limit=20`);
      setMessages(data.messages || []);
      setHasMore(data.has_more ?? false);
      setSkip(20);
    } catch (err) {
      console.error('Failed to load session messages:', err);
    } finally {
      setSelectedSessionLoading(false);
    }
  };

  const loadMore = async () => {
    if (loading || !hasMore || !currentSessionId) return;
    setLoading(true);
    try {
      const data = await authFetchJson(`/chat?session_id=${currentSessionId}&skip=${skip}&limit=20`);
      setMessages((prev) => [...prev, ...(data.messages || [])]);
      setHasMore(data.has_more ?? false);
      setSkip((prev) => prev + 20);
    } catch (err) {
      console.error('Failed to load more messages:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleNewSession = async () => {
    setCurrentSessionId(null);
    setMessages([]);
    setSkip(0);
    setHasMore(false);
    setTraceEvents([]);
    setLastRunId(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || loading) return;

    const pendingMessage: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: newMessage,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, pendingMessage]);
    setNewMessage('');
    setLoading(true);

    try {
      const payload: any = { message: pendingMessage.content };
      if (currentSessionId) {
        payload.session_id = currentSessionId;
      }
      const data = await authFetchJson('/chat', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      if (data.session_id) {
        setCurrentSessionId(data.session_id);
        await loadSessions();
      }

      const assistantMessage: ChatMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setTraceEvents(data.trace_events || []);
      setLastRunId(data.run_id || null);
    } catch (err) {
      alert(err instanceof Error ? err.message : '获取响应失败');
    } finally {
      setLoading(false);
    }
  };

  const renderSession = (session: ChatSession) => {
    const isActive = session.session_id === currentSessionId;
    return (
      <button
        key={session.session_id}
        className={`session-card ${session.expired ? 'expired' : ''} ${isActive ? 'active' : ''}`}
        onClick={() => loadSession(session.session_id)}
      >
        <div className="session-card-title">
          会话 {session.session_id.slice(0, 8)} {session.expired ? '(已过期)' : ''}
        </div>
        <div className="session-card-meta">
          更新时间：{new Date(session.updated_at).toLocaleString()}
        </div>
      </button>
    );
  };

  return (
    <section className="section">
      <div className="section-header">
        Chat
        <button className="submit-btn compact" type="button" onClick={handleNewSession}>
          新会话
        </button>
      </div>

      <div className="session-list">
        {sessions.length === 0 && <div className="empty-state">尚未创建会话，发送第一条消息即可开始。</div>}
        {sessions.map(renderSession)}
      </div>

      <div className="chat-messages" ref={messagesEndRef}>
        {selectedSessionLoading && <div className="loading-indicator">加载会话中...</div>}

        {!currentSessionId && !selectedSessionLoading && (
          <div className="empty-state">请选择一个会话或新建会话后发送消息。</div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`chat-message ${msg.role}`}>
            {msg.content}
          </div>
        ))}

        {hasMore && currentSessionId && (
          <div className="load-more">
            <button className="load-more-btn" onClick={loadMore} disabled={loading}>
              {loading ? '加载中...' : '加载更多历史'}
            </button>
          </div>
        )}

        {loading && !selectedSessionLoading && (
          <div className="loading-indicator">发送中...</div>
        )}
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

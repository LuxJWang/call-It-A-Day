import { useState } from 'react';
import { API_URL, setAuthToken } from '../api';

interface LoginSectionProps {
  onAuthenticated: (username: string) => void;
}

function LoginSection({ onAuthenticated }: LoginSectionProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('call_it_a_day');
  const [password, setPassword] = useState('call_it_a_day');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/users/${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || '请求失败');
      }

      const { token, username: returnedUsername } = await response.json();
      setAuthToken(token);
      onAuthenticated(returnedUsername);
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="section login-section">
      <div className="section-header">登录 / 注册</div>
      <div className="login-info">
        <p>默认公共账号：<strong>用户名</strong> 和 <strong>密码</strong> 都是 <code>call_it_a_day</code></p>
        <p>忘记密码请联系管理员：<a href="mailto:jinhuiwong@icloud.com">jinhuiwong@icloud.com</a></p>
      </div>
      <form onSubmit={handleSubmit} className="login-form">
        <label>
          用户名
          <input
            className="config-input"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
        </label>
        <label>
          密码
          <input
            className="config-input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error && <div className="error-message">{error}</div>}
        <div className="login-actions">
          <button className="submit-btn" type="submit" disabled={loading}>
            {loading ? '处理中...' : mode === 'login' ? '登录' : '注册'}
          </button>
          <button
            type="button"
            className="submit-btn compact"
            onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
          >
            切换到 {mode === 'login' ? '注册' : '登录'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default LoginSection;

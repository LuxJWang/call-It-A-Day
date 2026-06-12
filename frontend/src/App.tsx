import { useEffect, useState } from 'react';
import './App.css';
import DiarySection from './components/DiarySection';
import ChatSection from './components/ChatSection';
import ConfigSection from './components/ConfigSection';
import LoginSection from './components/LoginSection';
import { authFetchJson, getAuthToken, setAuthToken } from './api';

function App() {
  const [user, setUser] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      setLoading(false);
      return;
    }

    authFetchJson('/users/me')
      .then((data) => setUser(data.username))
      .catch(() => {
        setAuthToken(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleAuthenticated = (username: string) => {
    setUser(username);
  };

  const handleLogout = () => {
    setAuthToken(null);
    setUser(null);
  };

  if (loading) {
    return (
      <div className="app">
        <header className="app-header">
          <h1>Call It A Day</h1>
        </header>
        <main className="app-main">
          <div className="empty-state">正在验证登录状态...</div>
        </main>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="app">
        <header className="app-header">
          <h1>Call It A Day</h1>
        </header>
        <main className="app-main">
          <LoginSection onAuthenticated={handleAuthenticated} />
        </main>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-row">
          <h1>Call It A Day</h1>
          <button className="logout-btn" onClick={handleLogout}>登出</button>
        </div>
        <div className="app-user">当前用户：{user}</div>
      </header>
      <main className="app-main">
        <ConfigSection />
        <DiarySection />
        <ChatSection />
      </main>
    </div>
  );
}

export default App;

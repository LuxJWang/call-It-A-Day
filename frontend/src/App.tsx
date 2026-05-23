import './App.css'
import DiarySection from './components/DiarySection'
import ChatSection from './components/ChatSection'
import ConfigSection from './components/ConfigSection'

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>Call It A Day</h1>
      </header>
      <main className="app-main">
        <ConfigSection />
        <DiarySection />
        <ChatSection />
      </main>
    </div>
  )
}

export default App

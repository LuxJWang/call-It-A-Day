import './App.css'
import DiarySection from './components/DiarySection'
import ChatSection from './components/ChatSection'

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>Call It A Day</h1>
      </header>
      <main className="app-main">
        <DiarySection />
        <ChatSection />
      </main>
    </div>
  )
}

export default App

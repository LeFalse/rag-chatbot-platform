import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Chat, Documents, Dashboard } from './pages'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/chat" element={<Chat />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/" element={<Navigate to="/chat" replace />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App

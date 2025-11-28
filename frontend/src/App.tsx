import { useState, useEffect } from 'react'

interface HealthStatus {
  status: string
}

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/health`)
        const data = await response.json()
        setHealth(data)
      } catch (err) {
        setError('Backend not available')
      }
    }
    checkHealth()
  }, [])

  return (
    <div className="app">
      <header>
        <h1>RAG Chatbot Platform</h1>
      </header>
      <main>
        <section className="status-card">
          <h2>System Status</h2>
          {error ? (
            <p className="status error">{error}</p>
          ) : health ? (
            <p className="status ok">Backend: {health.status}</p>
          ) : (
            <p className="status loading">Checking...</p>
          )}
        </section>
        <section className="features">
          <h2>Features</h2>
          <ul>
            <li>Upload documents (PDF, TXT, MD)</li>
            <li>Chat with your documents using AI</li>
            <li>Switch between LLM providers</li>
            <li>Monitor usage metrics</li>
          </ul>
        </section>
      </main>
    </div>
  )
}

export default App

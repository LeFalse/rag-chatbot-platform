import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './Layout.css'

interface LayoutProps {
  children: React.ReactNode
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  return (
    <div className="layout">
      <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <h1 className="app-title">RAG Chat</h1>
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            ☰
          </button>
        </div>

        <nav className="sidebar-nav">
          <Link
            to="/chat"
            className={`nav-link ${isActive('/chat') ? 'active' : ''}`}
          >
            <span className="nav-icon">💬</span>
            <span className="nav-label">Chat</span>
          </Link>
          <Link
            to="/documents"
            className={`nav-link ${isActive('/documents') ? 'active' : ''}`}
          >
            <span className="nav-icon">📄</span>
            <span className="nav-label">Documents</span>
          </Link>
          <Link
            to="/dashboard"
            className={`nav-link ${isActive('/dashboard') ? 'active' : ''}`}
          >
            <span className="nav-icon">📊</span>
            <span className="nav-label">Dashboard</span>
          </Link>
        </nav>
      </aside>

      <main className="main-content">
        <header className="top-header">
          <div className="header-content">
            <h2 className="page-title">
              {location.pathname === '/chat'
                ? 'Chat Interface'
                : location.pathname === '/documents'
                  ? 'Document Management'
                  : 'Metrics Dashboard'}
            </h2>
          </div>
        </header>
        <div className="content-area">{children}</div>
      </main>
    </div>
  )
}

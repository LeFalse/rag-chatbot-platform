import React, { useState, useEffect } from 'react'
import { Card, CardBody, PageLoader, Button } from '../components/ui'
import { apiClient } from '../services/api'
import { MetricsData, ConversationMetrics, MessageMetrics } from '../types'
import './Dashboard.css'

export const Dashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<MetricsData | null>(null)
  const [conversations, setConversations] = useState<ConversationMetrics[]>([])
  const [selectedConversation, setSelectedConversation] = useState<ConversationMetrics | null>(null)
  const [messages, setMessages] = useState<MessageMetrics[]>([])
  const [selectedMessage, setSelectedMessage] = useState<MessageMetrics | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMessages, setIsLoadingMessages] = useState(false)

  useEffect(() => {
    loadMetrics()
  }, [])

  const loadMetrics = async () => {
    try {
      setIsLoading(true)
      const [aggregateData, conversationsData] = await Promise.all([
        apiClient.getAggregateMetrics(),
        apiClient.getConversationsMetrics(),
      ])
      setMetrics(aggregateData)
      setConversations(conversationsData)
    } catch (error) {
      console.error('Failed to load metrics:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const loadConversationMessages = async (conversation: ConversationMetrics) => {
    try {
      setIsLoadingMessages(true)
      setSelectedConversation(conversation)
      const messagesData = await apiClient.getConversationMessagesMetrics(conversation.id)
      setMessages(messagesData)
    } catch (error) {
      console.error('Failed to load conversation messages:', error)
    } finally {
      setIsLoadingMessages(false)
    }
  }

  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M'
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K'
    }
    return num.toString()
  }

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString('pt-BR')
  }

  if (isLoading) {
    return <PageLoader />
  }

  if (!metrics) {
    return (
      <Card>
        <CardBody>
          <p>No metrics available yet.</p>
        </CardBody>
      </Card>
    )
  }

  return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">Metrics Dashboard</h1>

      {/* Summary Cards */}
      <div className="metrics-grid">
        <Card className="metric-card">
          <CardBody>
            <h3>Messages</h3>
            <p className="metric-value">{formatNumber(metrics.messages_count)}</p>
            <span className="metric-label">Total messages</span>
          </CardBody>
        </Card>

        <Card className="metric-card">
          <CardBody>
            <h3>Documents</h3>
            <p className="metric-value">{formatNumber(metrics.documents_count)}</p>
            <span className="metric-label">Total documents</span>
          </CardBody>
        </Card>

        <Card className="metric-card">
          <CardBody>
            <h3>Collections</h3>
            <p className="metric-value">{formatNumber(metrics.collections_count)}</p>
            <span className="metric-label">Total collections</span>
          </CardBody>
        </Card>

        <Card className="metric-card">
          <CardBody>
            <h3>Avg Response Time</h3>
            <p className="metric-value">
              {formatNumber(metrics.average_response_time_ms)}
              <span className="metric-unit">ms</span>
            </p>
            <span className="metric-label">Average latency</span>
          </CardBody>
        </Card>

        <Card className="metric-card highlight-input">
          <CardBody>
            <h3>Input Tokens</h3>
            <p className="metric-value">{formatNumber(metrics.tokens_input)}</p>
            <span className="metric-label">Total input tokens</span>
          </CardBody>
        </Card>

        <Card className="metric-card highlight-output">
          <CardBody>
            <h3>Output Tokens</h3>
            <p className="metric-value">{formatNumber(metrics.tokens_output)}</p>
            <span className="metric-label">Total output tokens</span>
          </CardBody>
        </Card>
      </div>

      {/* Conversations Table */}
      <Card className="conversations-metrics-card">
        <CardBody>
          <div className="section-header">
            <h2>Conversations</h2>
            <Button size="small" variant="secondary" onClick={loadMetrics}>
              Refresh
            </Button>
          </div>

          {conversations.length === 0 ? (
            <p className="empty-text">No conversations yet. Start chatting to see metrics.</p>
          ) : (
            <div className="table-container">
              <table className="metrics-table">
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Messages</th>
                    <th>Input Tokens</th>
                    <th>Output Tokens</th>
                    <th>Avg Latency</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {conversations.map((conv) => (
                    <tr
                      key={conv.id}
                      className={selectedConversation?.id === conv.id ? 'selected' : ''}
                    >
                      <td className="title-cell">{conv.title}</td>
                      <td>{conv.message_count}</td>
                      <td className="tokens-input">{formatNumber(conv.tokens_input)}</td>
                      <td className="tokens-output">{formatNumber(conv.tokens_output)}</td>
                      <td>{conv.avg_latency_ms}ms</td>
                      <td>{formatDate(conv.created_at)}</td>
                      <td>
                        <Button
                          size="small"
                          variant="secondary"
                          onClick={() => loadConversationMessages(conv)}
                        >
                          View Details
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Messages Detail Modal */}
      {selectedConversation && (
        <div className="modal-overlay" onClick={() => setSelectedConversation(null)}>
          <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Messages: {selectedConversation.title}</h3>
              <button
                className="modal-close"
                onClick={() => setSelectedConversation(null)}
                aria-label="Close"
              >
                &times;
              </button>
            </div>
            <div className="modal-body">
              {isLoadingMessages ? (
                <div className="loading-messages">Loading messages...</div>
              ) : messages.length === 0 ? (
                <p className="empty-text">No messages in this conversation.</p>
              ) : (
                <div className="table-container">
                  <table className="metrics-table messages-table">
                    <thead>
                      <tr>
                        <th>Role</th>
                        <th>Content</th>
                        <th>Input</th>
                        <th>Output</th>
                        <th>Total</th>
                        <th>Latency</th>
                        <th>Model</th>
                        <th>Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {messages.map((msg) => (
                        <tr
                          key={msg.id}
                          className={`role-${msg.role} clickable-row`}
                          onClick={() => setSelectedMessage(msg)}
                        >
                          <td>
                            <span className={`role-badge ${msg.role}`}>{msg.role}</span>
                          </td>
                          <td className="content-cell">
                            {msg.content_preview || msg.content}
                          </td>
                          <td className="tokens-input">
                            {msg.tokens_input !== null ? formatNumber(msg.tokens_input) : '-'}
                          </td>
                          <td className="tokens-output">
                            {msg.tokens_output !== null ? formatNumber(msg.tokens_output) : '-'}
                          </td>
                          <td>
                            {msg.tokens_used !== null ? formatNumber(msg.tokens_used) : '-'}
                          </td>
                          <td>{msg.latency_ms !== null ? `${msg.latency_ms}ms` : '-'}</td>
                          <td>{msg.model || '-'}</td>
                          <td>{formatDate(msg.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <div className="conversation-summary">
                <span>
                  Total: <strong>{messages.length}</strong> messages
                </span>
                <span>
                  Input: <strong className="tokens-input">{formatNumber(selectedConversation.tokens_input)}</strong>
                </span>
                <span>
                  Output: <strong className="tokens-output">{formatNumber(selectedConversation.tokens_output)}</strong>
                </span>
              </div>
              <Button variant="secondary" onClick={() => setSelectedConversation(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Message Detail Modal */}
      {selectedMessage && (
        <div className="modal-overlay" onClick={() => setSelectedMessage(null)}>
          <div className="modal-content modal-message-detail" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>
                <span className={`role-badge ${selectedMessage.role}`}>{selectedMessage.role}</span>
                Message Details
              </h3>
              <button
                className="modal-close"
                onClick={() => setSelectedMessage(null)}
                aria-label="Close"
              >
                &times;
              </button>
            </div>
            <div className="modal-body message-detail-body">
              {/* Token Stats - Only for assistant messages */}
              {selectedMessage.role === 'assistant' ? (
                <div className="message-stats-grid">
                  <div className="stat-item">
                    <span className="stat-label">Input Tokens</span>
                    <span className="stat-value tokens-input">
                      {selectedMessage.tokens_input !== null ? formatNumber(selectedMessage.tokens_input) : '-'}
                    </span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Output Tokens</span>
                    <span className="stat-value tokens-output">
                      {selectedMessage.tokens_output !== null ? formatNumber(selectedMessage.tokens_output) : '-'}
                    </span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Total Tokens</span>
                    <span className="stat-value">
                      {selectedMessage.tokens_used !== null ? formatNumber(selectedMessage.tokens_used) : '-'}
                    </span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Latency</span>
                    <span className="stat-value">
                      {selectedMessage.latency_ms !== null ? `${selectedMessage.latency_ms}ms` : '-'}
                    </span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Model</span>
                    <span className="stat-value">{selectedMessage.model || '-'}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Time</span>
                    <span className="stat-value">{formatDate(selectedMessage.created_at)}</span>
                  </div>
                </div>
              ) : (
                <div className="message-stats-grid user-stats">
                  <div className="stat-item">
                    <span className="stat-label">Time</span>
                    <span className="stat-value">{formatDate(selectedMessage.created_at)}</span>
                  </div>
                </div>
              )}

              {/* Collection Config - Only for assistant messages */}
              {selectedMessage.role === 'assistant' && selectedMessage.collection_config && (
                <div className="collection-config-section">
                  <h4 className="config-section-title">Agent Configuration</h4>
                  <div className="config-grid">
                    <div className="config-item">
                      <span className="config-label">Collection</span>
                      <span className="config-value">{selectedMessage.collection_config.collection_name}</span>
                    </div>
                    <div className="config-item">
                      <span className="config-label">Personality</span>
                      <span className={`config-value personality-badge ${selectedMessage.collection_config.personality}`}>
                        {selectedMessage.collection_config.personality}
                      </span>
                    </div>
                    <div className="config-item">
                      <span className="config-label">Temperature</span>
                      <span className="config-value">{selectedMessage.collection_config.temperature}</span>
                    </div>
                    <div className="config-item">
                      <span className="config-label">Max Tokens</span>
                      <span className="config-value">{selectedMessage.collection_config.max_tokens}</span>
                    </div>
                    <div className="config-item">
                      <span className="config-label">Top K</span>
                      <span className="config-value">{selectedMessage.collection_config.top_k}</span>
                    </div>
                    {selectedMessage.collection_config.system_prompt && (
                      <div className="config-item full-width">
                        <span className="config-label">Custom Prompt</span>
                        <span className="config-value custom-prompt">{selectedMessage.collection_config.system_prompt}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Retrieved Context - Only for assistant messages */}
              {selectedMessage.role === 'assistant' && selectedMessage.context_chunks && selectedMessage.context_chunks.length > 0 && (
                <div className="context-chunks-simple">
                  <span className="context-label">Sources:</span>
                  {selectedMessage.context_chunks.map((chunk, index) => (
                    <span key={index} className={`context-tag ${chunk.similarity_score >= 0.7 ? 'high' : chunk.similarity_score >= 0.5 ? 'medium' : 'low'}`}>
                      {chunk.filename} ({(chunk.similarity_score * 100).toFixed(0)}%)
                    </span>
                  ))}
                </div>
              )}

              {/* For assistant messages: show prompt input and response */}
              {selectedMessage.role === 'assistant' && (
                <>
                  {/* Input (Prompt) - Collapsible */}
                  {selectedMessage.prompt_input && (
                    <details className="expandable-section">
                      <summary className="expandable-header">
                        <span className="expandable-title">Input (Full Prompt)</span>
                        <span className="expandable-hint">Click to expand</span>
                      </summary>
                      <div className="message-content-box">
                        <pre>{selectedMessage.prompt_input}</pre>
                      </div>
                    </details>
                  )}

                  {/* Output (Response) - Collapsible */}
                  <details className="expandable-section" open>
                    <summary className="expandable-header">
                      <span className="expandable-title">Response</span>
                      <span className="expandable-hint">Click to collapse</span>
                    </summary>
                    <div className="message-content-box">
                      <pre>{selectedMessage.content}</pre>
                    </div>
                  </details>
                </>
              )}

              {/* For user messages: show the question */}
              {selectedMessage.role === 'user' && (
                <details className="expandable-section" open>
                  <summary className="expandable-header">
                    <span className="expandable-title">User Question</span>
                    <span className="expandable-hint">Click to collapse</span>
                  </summary>
                  <div className="message-content-box">
                    <pre>{selectedMessage.content}</pre>
                  </div>
                </details>
              )}
            </div>
            <div className="modal-footer">
              <Button variant="secondary" onClick={() => setSelectedMessage(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

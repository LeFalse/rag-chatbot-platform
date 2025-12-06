import React, { useState, useEffect, useRef } from 'react'
import { Button, Card, CardBody, Loader, CreateConversationModal, LLMSelector, MarkdownRenderer, type LLMProvider } from '../components/ui'
import { apiClient } from '../services/api'
import { Collection, Conversation, Message } from '../types'
import './Chat.css'

interface Source {
  filename: string
  similarity_score: number
}

interface MessageWithSources extends Message {
  sources?: Source[]
}

export const Chat: React.FC = () => {
  const [collections, setCollections] = useState<Collection[]>([])
  const [selectedCollection, setSelectedCollection] = useState<string>('')
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversation, setSelectedConversation] = useState<string>('')
  const [messages, setMessages] = useState<MessageWithSources[]>([])
  const [newQuestion, setNewQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingCollections, setIsLoadingCollections] = useState(true)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isCreatingConversation, setIsCreatingConversation] = useState(false)
  const [llmProvider, setLlmProvider] = useState<LLMProvider>('ollama')
  const [deleteModal, setDeleteModal] = useState<Conversation | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load collections on mount
  useEffect(() => {
    loadCollections()
  }, [])

  // Load conversations when collection changes
  useEffect(() => {
    if (selectedCollection) {
      loadConversations()
    }
  }, [selectedCollection])

  // Load conversation history when conversation changes
  useEffect(() => {
    if (selectedConversation) {
      loadConversationHistory()
    }
  }, [selectedConversation])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadCollections = async () => {
    try {
      setIsLoadingCollections(true)
      const data = await apiClient.listCollections()
      setCollections(data)
      if (data.length > 0) {
        setSelectedCollection(data[0].id)
      }
    } catch (error) {
      console.error('Failed to load collections:', error)
    } finally {
      setIsLoadingCollections(false)
    }
  }

  const loadConversations = async () => {
    try {
      const data = await apiClient.listConversations(selectedCollection)
      setConversations(data)
      setMessages([])
    } catch (error) {
      console.error('Failed to load conversations:', error)
    }
  }

  const loadConversationHistory = async () => {
    try {
      const data = await apiClient.getConversationHistory(selectedConversation)
      setMessages(data.messages)
    } catch (error) {
      console.error('Failed to load conversation history:', error)
    }
  }

  const handleCreateConversation = async (title: string) => {
    setIsCreatingConversation(true)
    try {
      const conversation = await apiClient.createConversation(
        selectedCollection,
        title
      )
      setConversations([conversation, ...conversations])
      setSelectedConversation(conversation.id)
      setIsCreateModalOpen(false)
    } catch (error) {
      console.error('Failed to create conversation:', error)
    } finally {
      setIsCreatingConversation(false)
    }
  }

  const handleDeleteClick = (conv: Conversation, e: React.MouseEvent) => {
    e.stopPropagation()
    setDeleteModal(conv)
  }

  const handleConfirmDelete = async () => {
    if (!deleteModal) return

    try {
      setIsDeleting(true)
      await apiClient.deleteConversation(deleteModal.id)

      // Remove from local state
      setConversations(conversations.filter((c) => c.id !== deleteModal.id))

      // Clear selection if deleted conversation was selected
      if (selectedConversation === deleteModal.id) {
        setSelectedConversation('')
        setMessages([])
      }

      setDeleteModal(null)
    } catch (error) {
      console.error('Failed to delete conversation:', error)
    } finally {
      setIsDeleting(false)
    }
  }

  const handleSendQuestion = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newQuestion.trim() || !selectedConversation) return

    const userMessage: MessageWithSources = {
      id: Date.now().toString(),
      role: 'user',
      content: newQuestion,
      created_at: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    const question = newQuestion
    setNewQuestion('')
    setIsLoading(true)

    const assistantMsg: MessageWithSources = {
      id: `${Date.now()}-assistant`,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, assistantMsg])

    try {
      const stream = await apiClient.askQuestion(
        selectedConversation,
        question,
        5,
        0.5,
        llmProvider
      )

      let assistantContent = ''
      let sources: Source[] = []

      for await (const chunk of stream) {
        assistantContent += chunk

        // Check for sources marker and extract
        const sourcesMatch = assistantContent.match(/\[SOURCES\](.*?)\[\/SOURCES\]/)
        if (sourcesMatch) {
          try {
            const parsed = JSON.parse(sourcesMatch[1])
            sources = parsed.sources || []
            // Remove the sources marker from content
            assistantContent = assistantContent.replace(/\n?\[SOURCES\].*?\[\/SOURCES\]/, '')
          } catch (e) {
            console.error('Failed to parse sources:', e)
          }
        }

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsg.id
              ? { ...msg, content: assistantContent, sources }
              : msg
          )
        )
      }
    } catch (error) {
      console.error('Failed to send question:', error)
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsg.id
            ? {
                ...msg,
                content: `Error: ${error instanceof Error ? error.message : 'Failed to process question'}`,
              }
            : msg
        )
      )
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoadingCollections) {
    return (
      <div className="chat-loading">
        <Loader size="large" variant="spinner" />
        <p>Loading collections...</p>
      </div>
    )
  }

  if (collections.length === 0) {
    return (
      <div className="chat-empty">
        <Card>
          <CardBody>
            <h2>No Collections Available</h2>
            <p>Please create a collection first in the Documents section.</p>
          </CardBody>
        </Card>
      </div>
    )
  }

  return (
    <div className="chat-container">
      <div className="chat-sidebar">
        <div className="collection-selector">
          <label htmlFor="collection">Collection</label>
          <select
            id="collection"
            value={selectedCollection}
            onChange={(e) => setSelectedCollection(e.target.value)}
            className="select-input"
          >
            {collections.map((col) => (
              <option key={col.id} value={col.id}>
                {col.name}
              </option>
            ))}
          </select>
        </div>

        <div className="conversations-list">
          <div className="conversations-header">
            <h3>Conversations</h3>
            <Button
              size="small"
              variant="secondary"
              onClick={() => setIsCreateModalOpen(true)}
            >
              + New
            </Button>
          </div>
          {conversations.length === 0 ? (
            <p className="empty-text">No conversations yet</p>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                className={`conversation-item ${
                  selectedConversation === conv.id ? 'active' : ''
                }`}
                onClick={() => setSelectedConversation(conv.id)}
              >
                <span className="conversation-title">{conv.title}</span>
                <button
                  className="conversation-delete"
                  onClick={(e) => handleDeleteClick(conv, e)}
                  aria-label="Delete conversation"
                >
                  &times;
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="chat-main">
        {!selectedConversation ? (
          <div className="chat-welcome">
            <h2>Select or Create a Conversation</h2>
            <p>Choose an existing conversation or create a new one to start chatting.</p>
          </div>
        ) : (
          <>
            <div className="chat-header">
              <LLMSelector value={llmProvider} onChange={setLlmProvider} disabled={isLoading} />
            </div>
            <div className="messages-container">
              {messages.map((msg) => (
                <div key={msg.id} className={`message message-${msg.role}`}>
                  <div className="message-content">
                    {msg.role === 'assistant' ? (
                      <MarkdownRenderer content={msg.content} />
                    ) : (
                      msg.content
                    )}
                  </div>
                  {msg.sources && msg.sources.length > 0 && (
                    <details className="message-sources">
                      <summary className="sources-toggle">
                        Sources ({msg.sources.length})
                      </summary>
                      <div className="sources-list">
                        {msg.sources.map((source, idx) => (
                          <span
                            key={idx}
                            className={`source-tag ${source.similarity_score >= 0.7 ? 'high' : source.similarity_score >= 0.5 ? 'medium' : 'low'}`}
                          >
                            {source.filename} ({(source.similarity_score * 100).toFixed(0)}%)
                          </span>
                        ))}
                      </div>
                    </details>
                  )}
                  {msg.latency_ms && (
                    <div className="message-meta">
                      Response time: {msg.latency_ms}ms
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="message message-loading">
                  <Loader size="small" variant="spinner" />
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <form className="chat-input-form" onSubmit={handleSendQuestion}>
              <div className="input-wrapper">
                <input
                  type="text"
                  value={newQuestion}
                  onChange={(e) => setNewQuestion(e.target.value)}
                  placeholder="Ask a question about your documents..."
                  className="chat-input"
                  disabled={isLoading}
                />
                <Button
                  type="submit"
                  size="medium"
                  isLoading={isLoading}
                  disabled={!newQuestion.trim() || isLoading}
                >
                  Send
                </Button>
              </div>
            </form>
          </>
        )}
      </div>

      <CreateConversationModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onConfirm={handleCreateConversation}
        isLoading={isCreatingConversation}
      />

      {/* Delete Confirmation Modal */}
      {deleteModal && (
        <div className="modal-overlay" onClick={() => !isDeleting && setDeleteModal(null)}>
          <div className="modal-content modal-confirm" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Delete Conversation</h3>
              <button
                className="modal-close"
                onClick={() => setDeleteModal(null)}
                disabled={isDeleting}
                aria-label="Close"
              >
                &times;
              </button>
            </div>
            <div className="modal-body">
              <p className="confirm-message">
                Are you sure you want to delete <strong>{deleteModal.title}</strong>?
              </p>
              <p className="confirm-warning">
                This action cannot be undone. All messages in this conversation will be permanently removed.
              </p>
            </div>
            <div className="modal-footer">
              <Button
                variant="secondary"
                onClick={() => setDeleteModal(null)}
                disabled={isDeleting}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

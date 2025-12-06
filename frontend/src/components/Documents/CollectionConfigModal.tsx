import React, { useState, useEffect } from 'react'
import { Collection, PersonalityType, UpdateCollectionRequest } from '../../types'
import { Button } from '../ui'
import { apiClient } from '../../services/api'
import './CollectionConfigModal.css'

interface CollectionConfigModalProps {
  collection: Collection
  isOpen: boolean
  onClose: () => void
  onSave: (data: UpdateCollectionRequest) => Promise<void>
}

interface PersonalityOption {
  id: PersonalityType
  label: string
  icon: string
  description: string
  color: string
}

const PERSONALITY_OPTIONS: PersonalityOption[] = [
  {
    id: 'professional',
    label: 'Professional',
    icon: '💼',
    description: 'Formal, concise, and accurate responses',
    color: '#3b82f6',
  },
  {
    id: 'friendly',
    label: 'Friendly',
    icon: '😊',
    description: 'Conversational, helpful, and approachable',
    color: '#10b981',
  },
  {
    id: 'technical',
    label: 'Technical',
    icon: '⚙️',
    description: 'Detailed, precise, with technical terminology',
    color: '#8b5cf6',
  },
  {
    id: 'custom',
    label: 'Custom',
    icon: '✏️',
    description: 'Define your own system prompt',
    color: '#f59e0b',
  },
]

export const CollectionConfigModal: React.FC<CollectionConfigModalProps> = ({
  collection,
  isOpen,
  onClose,
  onSave,
}) => {
  const [name, setName] = useState(collection.name)
  const [description, setDescription] = useState(collection.description || '')
  const [personality, setPersonality] = useState<PersonalityType>(
    collection.personality || 'professional'
  )
  const [systemPrompt, setSystemPrompt] = useState(collection.system_prompt || '')
  const [temperature, setTemperature] = useState(collection.temperature)
  const [maxTokens, setMaxTokens] = useState(collection.max_tokens)
  const [topK, setTopK] = useState(collection.top_k)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [maxTokensLimit, setMaxTokensLimit] = useState(8192)

  // Fetch config limits on mount
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const config = await apiClient.getConfig()
        setMaxTokensLimit(config.max_tokens_limit)
      } catch (err) {
        console.error('Failed to fetch config:', err)
      }
    }
    fetchConfig()
  }, [])

  // MCP Configuration state
  const [gitlabEnabled, setGitlabEnabled] = useState(
    collection.mcp_config?.gitlab?.enabled ?? false
  )
  const [gitlabProjectId, setGitlabProjectId] = useState(
    collection.mcp_config?.gitlab?.project_id ?? ''
  )
  const [gitlabUrl, setGitlabUrl] = useState(
    collection.mcp_config?.gitlab?.gitlab_url ?? 'https://gitlab.com'
  )

  useEffect(() => {
    // Reset form when collection changes
    setName(collection.name)
    setDescription(collection.description || '')
    setPersonality(collection.personality || 'professional')
    setSystemPrompt(collection.system_prompt || '')
    setTemperature(collection.temperature)
    setMaxTokens(collection.max_tokens)
    setTopK(collection.top_k)
    setError(null)
    // MCP config
    setGitlabEnabled(collection.mcp_config?.gitlab?.enabled ?? false)
    setGitlabProjectId(collection.mcp_config?.gitlab?.project_id ?? '')
    setGitlabUrl(collection.mcp_config?.gitlab?.gitlab_url ?? 'https://gitlab.com')
  }, [collection])

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSaving(true)

    try {
      // Build MCP config if GitLab is enabled
      const mcpConfig = gitlabEnabled && gitlabProjectId.trim()
        ? {
            gitlab: {
              enabled: true,
              project_id: gitlabProjectId.trim(),
              gitlab_url: gitlabUrl.trim() || 'https://gitlab.com',
            },
          }
        : null

      await onSave({
        name,
        description: description || undefined,
        personality,
        // Send null explicitly when not custom to clear the old value
        system_prompt: personality === 'custom' ? systemPrompt : null,
        temperature,
        max_tokens: maxTokens,
        top_k: topK,
        mcp_config: mcpConfig,
      })
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration')
    } finally {
      setIsSaving(false)
    }
  }

  const getTemperatureLabel = (temp: number): string => {
    if (temp <= 0.2) return 'Precise'
    if (temp <= 0.5) return 'Balanced'
    if (temp <= 0.8) return 'Creative'
    return 'Very Creative'
  }

  return (
    <div className="config-modal-overlay" onClick={onClose}>
      <div className="config-modal" onClick={(e) => e.stopPropagation()}>
        <div className="config-modal-header">
          <div className="config-modal-title">
            <span className="config-icon">⚙️</span>
            <h2>Collection Settings</h2>
          </div>
          <button
            className="config-modal-close"
            onClick={onClose}
            disabled={isSaving}
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="config-modal-form">
          <div className="config-modal-body">
            {/* Basic Info Section */}
            <section className="config-section">
              <h3 className="config-section-title">Basic Information</h3>

              <div className="config-field">
                <label htmlFor="collection-name">Collection Name</label>
                <input
                  id="collection-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Technical Documentation"
                  required
                />
              </div>

              <div className="config-field">
                <label htmlFor="collection-description">Description</label>
                <textarea
                  id="collection-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional description for this collection"
                  rows={2}
                />
              </div>
            </section>

            {/* Personality Section */}
            <section className="config-section">
              <h3 className="config-section-title">Assistant Personality</h3>
              <p className="config-section-description">
                Choose how the assistant should respond to questions
              </p>

              <div className="personality-grid">
                {PERSONALITY_OPTIONS.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    className={`personality-card ${personality === option.id ? 'selected' : ''}`}
                    onClick={() => setPersonality(option.id)}
                    style={{
                      '--card-accent': option.color,
                    } as React.CSSProperties}
                  >
                    <span className="personality-icon">{option.icon}</span>
                    <span className="personality-label">{option.label}</span>
                    <span className="personality-description">{option.description}</span>
                  </button>
                ))}
              </div>

              {personality === 'custom' && (
                <div className="config-field custom-prompt-field">
                  <label htmlFor="system-prompt">Custom System Prompt</label>
                  <textarea
                    id="system-prompt"
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value)}
                    placeholder="Enter your custom instructions for the assistant..."
                    rows={4}
                  />
                  <span className="field-hint">
                    This prompt will be used instead of the personality presets
                  </span>
                </div>
              )}
            </section>

            {/* RAG Parameters Section */}
            <section className="config-section">
              <h3 className="config-section-title">RAG Parameters</h3>
              <p className="config-section-description">
                Fine-tune the retrieval and generation behavior
              </p>

              <div className="config-field slider-field">
                <div className="slider-header">
                  <label htmlFor="temperature">Temperature</label>
                  <span className="slider-value">
                    {temperature.toFixed(1)}
                    <span className="value-label">({getTemperatureLabel(temperature)})</span>
                  </span>
                </div>
                <input
                  id="temperature"
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="slider"
                />
                <div className="slider-labels">
                  <span>Precise</span>
                  <span>Creative</span>
                </div>
              </div>

              <div className="config-row">
                <div className="config-field">
                  <label htmlFor="top-k">Top K Documents</label>
                  <input
                    id="top-k"
                    type="number"
                    min={1}
                    max={20}
                    value={topK}
                    onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
                  />
                  <span className="field-hint">Number of document chunks to retrieve</span>
                </div>

                <div className="config-field">
                  <label htmlFor="max-tokens">Max Tokens</label>
                  <input
                    id="max-tokens"
                    type="number"
                    min={64}
                    max={maxTokensLimit}
                    step={64}
                    value={maxTokens}
                    onChange={(e) => setMaxTokens(parseInt(e.target.value) || 512)}
                  />
                  <span className="field-hint">Maximum response length (64-{maxTokensLimit})</span>
                </div>
              </div>
            </section>

            {/* MCP Integration Section */}
            <section className="config-section">
              <h3 className="config-section-title">Tool Integration (MCP)</h3>
              <p className="config-section-description">
                Enable repository access for code-aware responses
              </p>

              <div className="mcp-toggle-card">
                <div className="mcp-toggle-header">
                  <div className="mcp-toggle-info">
                    <span className="mcp-icon">🦊</span>
                    <div className="mcp-toggle-text">
                      <span className="mcp-toggle-label">GitLab Integration</span>
                      <span className="mcp-toggle-description">
                        Allow the assistant to search and read code from a GitLab repository
                      </span>
                    </div>
                  </div>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={gitlabEnabled}
                      onChange={(e) => setGitlabEnabled(e.target.checked)}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>

                {gitlabEnabled && (
                  <div className="mcp-config-fields">
                    <div className="config-field">
                      <label htmlFor="gitlab-project-id">Project Path</label>
                      <input
                        id="gitlab-project-id"
                        type="text"
                        value={gitlabProjectId}
                        onChange={(e) => setGitlabProjectId(e.target.value)}
                        placeholder="e.g., group/project or username/repo"
                        required={gitlabEnabled}
                      />
                      <span className="field-hint">
                        The GitLab project path (e.g., namespace/project-name)
                      </span>
                    </div>

                    <div className="config-field">
                      <label htmlFor="gitlab-url">GitLab URL</label>
                      <input
                        id="gitlab-url"
                        type="text"
                        value={gitlabUrl}
                        onChange={(e) => setGitlabUrl(e.target.value)}
                        placeholder="https://gitlab.com"
                      />
                      <span className="field-hint">
                        Self-hosted GitLab instance URL (default: gitlab.com)
                      </span>
                    </div>

                    <div className="mcp-info-box">
                      <span className="info-icon">ℹ️</span>
                      <span>
                        A GitLab Personal Access Token with <code>read_api</code> scope must be
                        configured in the server environment (GITLAB_TOKEN).
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </section>

            {error && (
              <div className="config-error">
                <span className="error-icon">!</span>
                {error}
              </div>
            )}
          </div>

          <div className="config-modal-footer">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isSaving || !name.trim()}
            >
              {isSaving ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

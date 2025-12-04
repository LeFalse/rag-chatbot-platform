import React, { useState, useEffect } from 'react'
import { Collection, PersonalityType, UpdateCollectionRequest } from '../../types'
import { Button } from '../ui'
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
  }, [collection])

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSaving(true)

    try {
      await onSave({
        name,
        description: description || undefined,
        personality,
        system_prompt: personality === 'custom' ? systemPrompt : undefined,
        temperature,
        max_tokens: maxTokens,
        top_k: topK,
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
                    max={4096}
                    step={64}
                    value={maxTokens}
                    onChange={(e) => setMaxTokens(parseInt(e.target.value) || 512)}
                  />
                  <span className="field-hint">Maximum response length</span>
                </div>
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

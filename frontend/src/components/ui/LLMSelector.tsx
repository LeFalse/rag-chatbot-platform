import React, { useEffect, useState } from 'react'
import './LLMSelector.css'
import { apiClient } from '../../services/api'

export type LLMProvider = 'ollama' | 'openai'

interface LLMSelectorProps {
  value: LLMProvider
  onChange: (provider: LLMProvider) => void
  disabled?: boolean
}

interface LLMProviderConfig {
  value: LLMProvider
  label: string
  icon: string
  description: string
}

export const LLMSelector: React.FC<LLMSelectorProps> = ({ value, onChange, disabled = false }) => {
  const [ollamaModel, setOllamaModel] = useState<string>('Loading...')

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const config = await apiClient.getConfig()
        setOllamaModel(config.llm_model || config.ollama_model)
      } catch (error) {
        console.error('Failed to fetch config:', error)
        setOllamaModel('Unknown')
      }
    }
    fetchConfig()
  }, [])

  const providers: LLMProviderConfig[] = [
    {
      value: 'ollama',
      label: 'Ollama',
      icon: '🦙',
      description: `Local LLM - ${ollamaModel}`,
    },
    {
      value: 'openai',
      label: 'OpenAI',
      icon: '🤖',
      description: 'GPT-4 - Most Capable',
    },
  ]

  return (
    <div className="llm-selector">
      <label className="llm-label">AI Model</label>
      <div className="llm-options">
        {providers.map((provider) => (
          <button
            key={provider.value}
            className={`llm-option ${value === provider.value ? 'active' : ''}`}
            onClick={() => onChange(provider.value)}
            disabled={disabled}
            title={provider.description}
          >
            <span className="llm-icon">{provider.icon}</span>
            <span className="llm-name">{provider.label}</span>
          </button>
        ))}
      </div>
      <p className="llm-description">
        {providers.find((p) => p.value === value)?.description}
      </p>
    </div>
  )
}

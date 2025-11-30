import React from 'react'
import './LLMSelector.css'

export type LLMProvider = 'ollama' | 'openai'

interface LLMSelectorProps {
  value: LLMProvider
  onChange: (provider: LLMProvider) => void
  disabled?: boolean
}

const LLM_PROVIDERS: { value: LLMProvider; label: string; icon: string; description: string }[] = [
  {
    value: 'ollama',
    label: 'Ollama',
    icon: '🦙',
    description: 'Local LLM - Fast & Private',
  },
  {
    value: 'openai',
    label: 'OpenAI',
    icon: '🤖',
    description: 'GPT-4 - Most Capable',
  },
]

export const LLMSelector: React.FC<LLMSelectorProps> = ({ value, onChange, disabled = false }) => {
  return (
    <div className="llm-selector">
      <label className="llm-label">AI Model</label>
      <div className="llm-options">
        {LLM_PROVIDERS.map((provider) => (
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
        {LLM_PROVIDERS.find((p) => p.value === value)?.description}
      </p>
    </div>
  )
}

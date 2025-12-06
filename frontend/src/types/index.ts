export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  latency_ms?: number
  model?: string
}

export interface Conversation {
  id: string
  collection_id: string
  title: string
  message_count: number
  created_at: string
  updated_at: string
}

export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface Document {
  id: string
  filename: string
  collection_id: string
  chunk_count: number
  status: DocumentStatus
  error: string | null
  created_at: string
}

export type PersonalityType = 'professional' | 'friendly' | 'technical' | 'custom'

// MCP (Model Context Protocol) configuration types
export interface GitLabMCPConfig {
  enabled: boolean
  project_id: string
  gitlab_url: string
}

export interface MCPConfig {
  gitlab?: GitLabMCPConfig | null
}

export interface Collection {
  id: string
  name: string
  description?: string
  embedding_model: string
  embedding_dimension: number
  document_count: number
  // Agent configuration
  system_prompt?: string
  personality?: PersonalityType
  temperature: number
  max_tokens: number
  top_k: number
  // MCP configuration
  mcp_config?: MCPConfig | null
  created_at: string
}

export interface UpdateCollectionRequest {
  name?: string
  description?: string
  system_prompt?: string | null
  personality?: PersonalityType
  temperature?: number
  max_tokens?: number
  top_k?: number
  mcp_config?: MCPConfig | null
}

export interface MetricsData {
  date: string
  messages_count: number
  documents_count: number
  collections_count: number
  average_response_time_ms: number
  token_usage: number
  tokens_input: number
  tokens_output: number
}

export interface ConversationMetrics {
  id: string
  title: string
  created_at: string | null
  message_count: number
  tokens_input: number
  tokens_output: number
  avg_latency_ms: number
}

export interface ContextChunk {
  filename: string
  similarity_score: number
  content_preview: string
}

export interface CollectionConfig {
  collection_name: string
  personality: PersonalityType
  temperature: number
  max_tokens: number
  top_k: number
  system_prompt: string | null
}

export interface MessageMetrics {
  id: string
  role: string
  content: string
  content_preview: string
  prompt_input: string | null
  context_chunks: ContextChunk[] | null
  tokens_input: number | null
  tokens_output: number | null
  tokens_used: number | null
  latency_ms: number | null
  model: string | null
  created_at: string | null
  collection_config: CollectionConfig | null
}

export interface ConversationHistory {
  conversation_id: string
  messages: Message[]
}

export interface ApiError {
  detail: string
}

export interface ProcessDocumentResponse {
  document_id: string
  chunk_count: number
  embeddings_generated: number
  status: DocumentStatus
  message: string
}

export interface DocumentContent {
  document_id: string
  filename: string
  content: string
  content_type: string | null
}

export interface AppConfig {
  llm_model: string
  ollama_model: string
  embedding_model: string
  max_tokens_default: number
  max_tokens_limit: number
}

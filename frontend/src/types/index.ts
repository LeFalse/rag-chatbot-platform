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

export interface Collection {
  id: string
  name: string
  embedding_model: string
  embedding_dimension: number
  document_count: number
  created_at: string
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

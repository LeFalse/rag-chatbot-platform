import axios, { AxiosInstance } from 'axios'
import {
  AppConfig,
  Collection,
  Conversation,
  Document,
  ConversationHistory,
  MetricsData,
  ConversationMetrics,
  MessageMetrics,
  ProcessDocumentResponse,
  DocumentContent,
  UpdateCollectionRequest,
} from '../types'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8050'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  // Health check
  async checkHealth(): Promise<{ status: string }> {
    const response = await this.client.get('/health')
    return response.data
  }

  // Config
  async getConfig(): Promise<AppConfig> {
    const response = await this.client.get('/config')
    return response.data
  }

  // Collections
  async createCollection(
    name: string,
    embedding_model: string,
    embedding_dimension: number
  ): Promise<Collection> {
    const response = await this.client.post('/documents/collections', {
      name,
      embedding_model,
      embedding_dimension,
    })
    return response.data
  }

  async listCollections(): Promise<Collection[]> {
    const response = await this.client.get('/documents/collections')
    return response.data
  }

  async updateCollection(
    collection_id: string,
    data: UpdateCollectionRequest
  ): Promise<Collection> {
    const response = await this.client.put(
      `/documents/collections/${collection_id}`,
      data
    )
    return response.data
  }

  async deleteCollection(
    collection_id: string
  ): Promise<{ message: string }> {
    const response = await this.client.delete(
      `/documents/collections/${collection_id}`
    )
    return response.data
  }

  // Documents
  async uploadDocument(
    collection_id: string,
    file: File
  ): Promise<Document> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await this.client.post(
      `/documents/${collection_id}/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
    return response.data
  }

  async listDocuments(collection_id: string): Promise<Document[]> {
    const response = await this.client.get(`/documents/${collection_id}`)
    return response.data
  }

  async deleteDocument(document_id: string): Promise<{ message: string }> {
    const response = await this.client.delete(`/documents/${document_id}`)
    return response.data
  }

  async processDocument(document_id: string): Promise<ProcessDocumentResponse> {
    const response = await this.client.post(`/documents/${document_id}/process`)
    return response.data
  }

  async getDocumentContent(document_id: string): Promise<DocumentContent> {
    const response = await this.client.get(`/documents/${document_id}/content`)
    return response.data
  }

  // Conversations
  async createConversation(
    collection_id: string,
    title: string
  ): Promise<Conversation> {
    const response = await this.client.post('/chat/conversations', {
      collection_id,
      title,
    })
    return response.data
  }

  async listConversations(collection_id: string): Promise<Conversation[]> {
    const response = await this.client.get('/chat/conversations', {
      params: { collection_id },
    })
    return response.data
  }

  async getConversationHistory(
    conversation_id: string
  ): Promise<ConversationHistory> {
    const response = await this.client.get(
      `/chat/conversations/${conversation_id}/history`
    )
    return response.data
  }

  async deleteConversation(
    conversation_id: string
  ): Promise<{ message: string }> {
    const response = await this.client.delete(
      `/chat/conversations/${conversation_id}`
    )
    return response.data
  }

  // Chat - Streaming
  async askQuestion(
    conversation_id: string,
    question: string,
    top_k: number = 3,
    similarity_threshold: number = 0.7,
    llmProvider: string = 'ollama'
  ): Promise<AsyncIterable<string>> {
    const response = await fetch(
      `${API_URL}/chat/conversations/${conversation_id}/ask`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question,
          top_k,
          similarity_threshold,
          llm_provider: llmProvider,
        }),
      }
    )

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`)
    }

    return this.readStream(response)
  }

  private async *readStream(response: Response): AsyncIterable<string> {
    const reader = response.body?.getReader()
    if (!reader) throw new Error('No response body')

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        yield new TextDecoder().decode(value)
      }
    } finally {
      reader.releaseLock()
    }
  }

  // Metrics
  async getDailyMetrics(days: number = 7): Promise<MetricsData[]> {
    const response = await this.client.get('/metrics/daily', {
      params: { days },
    })
    return response.data
  }

  async getAggregateMetrics(): Promise<MetricsData> {
    const response = await this.client.get('/metrics/aggregate')
    return response.data
  }

  async getConversationsMetrics(): Promise<ConversationMetrics[]> {
    const response = await this.client.get('/metrics/conversations')
    return response.data
  }

  async getConversationMessagesMetrics(conversationId: string): Promise<MessageMetrics[]> {
    const response = await this.client.get(`/metrics/conversations/${conversationId}`)
    return response.data
  }
}

export const apiClient = new ApiClient()

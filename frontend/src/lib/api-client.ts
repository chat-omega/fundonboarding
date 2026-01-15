// API client for the Intelligent Fund Onboarding System

import {
  ChatSession,
  SessionCreateResponse,
  FileUploadResponse
} from './chat-types';

class ApiClient {
  private baseUrl: string;
  
  constructor(baseUrl: string = '/api/onboarding') {
    this.baseUrl = baseUrl;
  }

  // Session Management
  async createSession(): Promise<SessionCreateResponse> {
    const response = await fetch(`${this.baseUrl}/session/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.statusText}`);
    }

    return response.json();
  }

  async getSessionStatus(sessionId: string): Promise<ChatSession> {
    const response = await fetch(`${this.baseUrl}/session/${sessionId}/status`);

    if (!response.ok) {
      throw new Error(`Failed to get session status: ${response.statusText}`);
    }

    return response.json();
  }

  async deleteSession(sessionId: string): Promise<{ session_id: string; status: string }> {
    const response = await fetch(`${this.baseUrl}/session/${sessionId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to delete session: ${response.statusText}`);
    }

    return response.json();
  }

  // File Upload
  async uploadFile(sessionId: string, file: File): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/upload?session_id=${sessionId}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Failed to upload file: ${response.statusText}`);
    }

    return response.json();
  }

  // Processing
  async startProcessing(sessionId: string, action: string = 'upload_file', data: Record<string, unknown> = {}) {
    const response = await fetch(`${this.baseUrl}/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        action,
        data,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to start processing: ${response.statusText}`);
    }

    return response.json();
  }

  // Chat
  async sendChatMessage(sessionId: string, message: string, metadata: Record<string, unknown> = {}) {
    const response = await fetch(`${this.baseUrl}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        message,
        metadata,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to send chat message: ${response.statusText}`);
    }

    return response.json();
  }

  async getChatHistory(sessionId: string): Promise<{ session_id: string; chat_history: Record<string, unknown>[] }> {
    const response = await fetch(`${this.baseUrl}/session/${sessionId}/chat`);

    if (!response.ok) {
      throw new Error(`Failed to get chat history: ${response.statusText}`);
    }

    return response.json();
  }

  // Data Retrieval
  async getPortfolioData(sessionId: string) {
    const response = await fetch(`${this.baseUrl}/session/${sessionId}/portfolio`);

    if (!response.ok) {
      throw new Error(`Failed to get portfolio data: ${response.statusText}`);
    }

    return response.json();
  }

  async getFundData(sessionId: string) {
    const response = await fetch(`${this.baseUrl}/session/${sessionId}/funds`);

    if (!response.ok) {
      throw new Error(`Failed to get fund data: ${response.statusText}`);
    }

    return response.json();
  }

  // SSE Stream Connection
  createEventSource(sessionId: string): EventSource {
    return new EventSource(`${this.baseUrl}/enhanced-stream/${sessionId}`);
  }

  // Test endpoint
  async createTestSession(): Promise<SessionCreateResponse & { sample_file: string; message: string }> {
    const response = await fetch(`${this.baseUrl}/test-sample`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to create test session: ${response.statusText}`);
    }

    return response.json();
  }

  // Health check
  async healthCheck() {
    const response = await fetch(`${this.baseUrl}/health`);

    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }

    return response.json();
  }
}

// SSE Event Handler Helper
export class SSEHandler {
  private eventSource: EventSource | null = null;
  private messageHandlers: Map<string, (data: Record<string, unknown>) => void> = new Map();

  connect(sessionId: string, apiClient: ApiClient) {
    this.disconnect(); // Ensure we don't have duplicate connections
    
    this.eventSource = apiClient.createEventSource(sessionId);
    
    this.eventSource.onopen = () => {
      console.log('SSE connection opened');
      this.trigger('connected', { sessionId });
    };

    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.trigger('message', data);
        
        // Trigger specific event type handlers
        if (data.type) {
          this.trigger(data.type, data.data || data);
        }
      } catch (error) {
        console.error('Failed to parse SSE message:', error);
      }
    };

    this.eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      this.trigger('error', { error });
    };
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  on(event: string, handler: (data: Record<string, unknown>) => void) {
    this.messageHandlers.set(event, handler);
  }

  off(event: string) {
    this.messageHandlers.delete(event);
  }

  private trigger(event: string, data: Record<string, unknown>) {
    const handler = this.messageHandlers.get(event);
    if (handler) {
      handler(data);
    }
  }

  isConnected(): boolean {
    return this.eventSource?.readyState === EventSource.OPEN;
  }
}

export const apiClient = new ApiClient();
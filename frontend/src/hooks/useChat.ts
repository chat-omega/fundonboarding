"use client";

import { useState, useCallback, useEffect, useRef } from 'react';
import { 
  ChatMessage, 
  ChatSession, 
  OnboardingStage, 
  SessionStatus,
  QuickAction 
} from '@/lib/chat-types';
import { apiClient } from '@/lib/api-client';
import { generateUUID } from '@/lib/utils';

interface UseChatOptions {
  autoCreateSession?: boolean;
  sessionId?: string;
}

export function useChat(options: UseChatOptions = {}) {
  const [session, setSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  
  const sessionRef = useRef<string | null>(options.sessionId || null);

  // Initialize session
  const createSession = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.createSession();
      sessionRef.current = response.session_id;
      
      const sessionData = await apiClient.getSessionStatus(response.session_id);
      setSession(sessionData);
      
      // Add welcome message
      const welcomeMessage: ChatMessage = {
        id: generateUUID(),
        role: 'assistant',
        content: `Welcome to the Intelligent Fund Onboarding System! 👋

I'm here to help you analyze your portfolio and extract detailed fund information. You can:

📊 **Upload a CSV/Excel file** with your portfolio holdings
📄 **Upload PDF prospectuses** for individual fund analysis
🔍 **Ask questions** about fund analysis and recommendations

What would you like to start with today?`,
        timestamp: new Date(),
        type: 'text',
        metadata: { session_id: response.session_id }
      };
      
      setMessages([welcomeMessage]);
      setIsConnected(true);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create session');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Load existing session
  const loadSession = useCallback(async (sessionId: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const sessionData = await apiClient.getSessionStatus(sessionId);
      setSession(sessionData);
      sessionRef.current = sessionId;
      
      // Load chat history if available
      const chatHistory = await apiClient.getChatHistory(sessionId);
      if (chatHistory.chat_history?.length > 0) {
        const chatMessages: ChatMessage[] = chatHistory.chat_history.map((msg: any) => ({
          id: generateUUID(),
          role: msg.role,
          content: msg.content,
          timestamp: new Date(msg.timestamp),
          type: 'text',
          metadata: msg.metadata || {}
        }));
        setMessages(chatMessages);
      }
      
      setIsConnected(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load session');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Send message
  const sendMessage = useCallback(async (content: string, type: 'text' | 'file_upload' = 'text', metadata: any = {}) => {
    if (!sessionRef.current) {
      await createSession();
      if (!sessionRef.current) return;
    }

    const userMessage: ChatMessage = {
      id: generateUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
      type,
      metadata: { ...metadata, session_id: sessionRef.current }
    };

    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);
    setError(null);

    try {
      const response = await apiClient.sendChatMessage(sessionRef.current, content, metadata);
      
      const assistantMessage: ChatMessage = {
        id: generateUUID(),
        role: 'assistant',
        content: response.message || 'I received your message and I\'m processing it.',
        timestamp: new Date(),
        type: response.message_type || 'text',
        metadata: { 
          session_id: sessionRef.current,
          ...response 
        }
      };

      setMessages(prev => [...prev, assistantMessage]);
      
    } catch (err) {
      const errorMessage: ChatMessage = {
        id: generateUUID(),
        role: 'system',
        content: `Error: ${err instanceof Error ? err.message : 'Failed to send message'}`,
        timestamp: new Date(),
        type: 'error',
        metadata: { session_id: sessionRef.current }
      };
      
      setMessages(prev => [...prev, errorMessage]);
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setIsTyping(false);
    }
  }, [createSession]);

  // Upload file
  const uploadFile = useCallback(async (file: File) => {
    if (!sessionRef.current) {
      await createSession();
      if (!sessionRef.current) return;
    }

    // Add file upload message
    const uploadMessage: ChatMessage = {
      id: generateUUID(),
      role: 'user',
      content: `Uploading: ${file.name}`,
      timestamp: new Date(),
      type: 'file_upload',
      metadata: {
        file_name: file.name,
        file_size: file.size,
        file_type: file.type,
        session_id: sessionRef.current
      }
    };

    setMessages(prev => [...prev, uploadMessage]);
    setIsTyping(true);

    try {
      const response = await apiClient.uploadFile(sessionRef.current, file);
      
      const successMessage: ChatMessage = {
        id: generateUUID(),
        role: 'assistant',
        content: `Great! I've received your ${file.name} file. Let me process it now...`,
        timestamp: new Date(),
        type: 'text',
        metadata: {
          file_path: response.file_path,
          file_type: response.file_type,
          session_id: sessionRef.current
        }
      };

      setMessages(prev => [...prev, successMessage]);
      
      // Start processing
      await apiClient.startProcessing(sessionRef.current);
      
    } catch (err) {
      const errorMessage: ChatMessage = {
        id: generateUUID(),
        role: 'system',
        content: `Failed to upload file: ${err instanceof Error ? err.message : 'Unknown error'}`,
        timestamp: new Date(),
        type: 'error',
        metadata: { session_id: sessionRef.current }
      };
      
      setMessages(prev => [...prev, errorMessage]);
      setError(err instanceof Error ? err.message : 'Failed to upload file');
    } finally {
      setIsTyping(false);
    }
  }, [createSession]);

  // Add system message (for status updates from SSE)
  const addSystemMessage = useCallback((content: string, type: 'status' | 'error' | 'success' = 'status', metadata: any = {}) => {
    const systemMessage: ChatMessage = {
      id: generateUUID(),
      role: 'system',
      content,
      timestamp: new Date(),
      type,
      metadata: { ...metadata, session_id: sessionRef.current }
    };

    setMessages(prev => [...prev, systemMessage]);
  }, []);

  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  // Refresh session
  const refreshSession = useCallback(async () => {
    if (sessionRef.current) {
      await loadSession(sessionRef.current);
    }
  }, [loadSession]);

  // Auto-create session on mount
  useEffect(() => {
    if (options.autoCreateSession && !sessionRef.current) {
      createSession();
    } else if (options.sessionId) {
      loadSession(options.sessionId);
    }
  }, [options.autoCreateSession, options.sessionId, createSession, loadSession]);

  return {
    // State
    session,
    messages,
    isLoading,
    isConnected,
    error,
    isTyping,
    sessionId: sessionRef.current,
    
    // Actions
    createSession,
    loadSession,
    sendMessage,
    uploadFile,
    addSystemMessage,
    clearMessages,
    refreshSession,
    
    // Helpers
    canUpload: isConnected && !isLoading,
    canSendMessage: isConnected && !isLoading && !isTyping
  };
}
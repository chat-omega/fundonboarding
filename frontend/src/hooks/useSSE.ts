"use client";

import { useEffect, useRef, useCallback, useState } from 'react';
import { SSEHandler } from '@/lib/api-client';
import { AgentMessage } from '@/lib/chat-types';

interface UseSSEOptions {
  onMessage?: (message: AgentMessage) => void;
  onConnected?: (sessionId: string) => void;
  onError?: (error: any) => void;
  onStatusUpdate?: (data: any) => void;
  onPortfolioProcessed?: (data: any) => void;
  onFundExtracted?: (data: any) => void;
  onAnalysisComplete?: (data: any) => void;
  onChatResponse?: (data: any) => void;
  onCategorizationQuestion?: (data: any) => void;
  onCategorizationComplete?: (data: any) => void;
  autoReconnect?: boolean;
  reconnectDelay?: number;
}

export function useSSE(sessionId: string | null, options: UseSSEOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [lastMessage, setLastMessage] = useState<AgentMessage | null>(null);
  const [messageCount, setMessageCount] = useState(0);
  
  const sseHandlerRef = useRef<SSEHandler | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);

  const {
    onMessage,
    onConnected,
    onError,
    onStatusUpdate,
    onPortfolioProcessed,
    onFundExtracted,
    onAnalysisComplete,
    onChatResponse,
    onCategorizationQuestion,
    onCategorizationComplete,
    autoReconnect = true,
    reconnectDelay = 5000
  } = options;

  // Connect to SSE stream
  const connect = useCallback(async () => {
    if (!sessionId) return;

    try {
      setConnectionStatus('connecting');
      
      if (sseHandlerRef.current) {
        sseHandlerRef.current.disconnect();
      }

      sseHandlerRef.current = new SSEHandler();
      
      // Set up event handlers
      sseHandlerRef.current.on('connected', (data: any) => {
        console.log('SSE connected:', data);
        setIsConnected(true);
        setConnectionStatus('connected');
        reconnectAttemptsRef.current = 0;
        onConnected?.(data.sessionId);
      });

      sseHandlerRef.current.on('message', (message: AgentMessage) => {
        setLastMessage(message);
        setMessageCount(prev => prev + 1);
        onMessage?.(message);
      });

      sseHandlerRef.current.on('status', (data: any) => {
        onStatusUpdate?.(data);
      });

      sseHandlerRef.current.on('portfolio_processed', (data: any) => {
        onPortfolioProcessed?.(data);
      });

      sseHandlerRef.current.on('fund_extracted', (data: any) => {
        onFundExtracted?.(data);
      });

      sseHandlerRef.current.on('analysis_complete', (data: any) => {
        onAnalysisComplete?.(data);
      });

      sseHandlerRef.current.on('chat_response', (data: any) => {
        onChatResponse?.(data);
      });

      sseHandlerRef.current.on('categorization_question', (data: any) => {
        onCategorizationQuestion?.(data);
      });

      sseHandlerRef.current.on('categorization_complete', (data: any) => {
        onCategorizationComplete?.(data);
      });

      sseHandlerRef.current.on('error', (error: any) => {
        console.error('SSE error:', error);
        setIsConnected(false);
        setConnectionStatus('error');
        onError?.(error);
        
        // Auto-reconnect
        if (autoReconnect) {
          scheduleReconnect();
        }
      });

      // Import apiClient dynamically to avoid circular dependency
      const { apiClient } = await import('@/lib/api-client');
      sseHandlerRef.current.connect(sessionId, apiClient);

    } catch (error) {
      console.error('Failed to connect SSE:', error);
      setConnectionStatus('error');
      onError?.(error);
      
      if (autoReconnect) {
        scheduleReconnect();
      }
    }
  }, [sessionId, onMessage, onConnected, onError, onStatusUpdate, onPortfolioProcessed, onFundExtracted, onAnalysisComplete, onChatResponse, onCategorizationQuestion, onCategorizationComplete, autoReconnect]);

  // Disconnect from SSE stream
  const disconnect = useCallback(() => {
    if (sseHandlerRef.current) {
      sseHandlerRef.current.disconnect();
      sseHandlerRef.current = null;
    }
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    setIsConnected(false);
    setConnectionStatus('disconnected');
  }, []);

  // Schedule reconnection
  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) return;

    const maxAttempts = 10;
    const delay = Math.min(reconnectDelay * Math.pow(1.5, reconnectAttemptsRef.current), 60000);

    if (reconnectAttemptsRef.current < maxAttempts) {
      console.log(`Scheduling reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxAttempts})`);
      
      reconnectTimeoutRef.current = setTimeout(() => {
        reconnectAttemptsRef.current += 1;
        reconnectTimeoutRef.current = null;
        connect();
      }, delay);
    } else {
      console.log('Max reconnection attempts reached');
      setConnectionStatus('error');
    }
  }, [connect, reconnectDelay]);

  // Force reconnect
  const reconnect = useCallback(() => {
    disconnect();
    setTimeout(connect, 100);
  }, [connect, disconnect]);

  // Send custom message through SSE (if supported by backend)
  const sendSSEMessage = useCallback((type: string, data: any) => {
    if (sseHandlerRef.current && isConnected) {
      // This would require backend support for bidirectional SSE
      console.log('SSE send not implemented yet:', type, data);
    }
  }, [isConnected]);

  // Effect to manage connection
  useEffect(() => {
    if (sessionId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [sessionId, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (sseHandlerRef.current) {
        sseHandlerRef.current.disconnect();
      }
    };
  }, []);

  // Check connection health periodically
  useEffect(() => {
    if (!isConnected || !sseHandlerRef.current) return;

    const healthCheckInterval = setInterval(() => {
      if (sseHandlerRef.current && !sseHandlerRef.current.isConnected()) {
        console.log('SSE connection lost, attempting to reconnect...');
        setIsConnected(false);
        setConnectionStatus('error');
        if (autoReconnect) {
          scheduleReconnect();
        }
      }
    }, 10000); // Check every 10 seconds

    return () => clearInterval(healthCheckInterval);
  }, [isConnected, autoReconnect, scheduleReconnect]);

  return {
    // Connection state
    isConnected,
    connectionStatus,
    reconnectAttempts: reconnectAttemptsRef.current,
    
    // Message data
    lastMessage,
    messageCount,
    
    // Actions
    connect,
    disconnect,
    reconnect,
    sendSSEMessage,
    
    // Helpers
    isConnecting: connectionStatus === 'connecting',
    hasError: connectionStatus === 'error'
  };
}
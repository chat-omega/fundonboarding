"use client";

import { useState, useRef, useCallback, KeyboardEvent } from 'react';
import { Send, Paperclip, Loader } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MessageInputProps {
  onSendMessage: (message: string) => void;
  onUploadFile: () => void;
  canSend?: boolean;
  canUpload?: boolean;
  isTyping?: boolean;
  placeholder?: string;
  className?: string;
}

export function MessageInput({
  onSendMessage,
  onUploadFile,
  canSend = true,
  canUpload = true,
  isTyping = false,
  placeholder = "Type your message...",
  className
}: MessageInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Handle message send
  const handleSend = useCallback(() => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || !canSend || isTyping) return;

    onSendMessage(trimmedMessage);
    setMessage('');
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [message, canSend, isTyping, onSendMessage]);

  // Handle keyboard events
  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  // Auto-resize textarea
  const handleTextareaChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setMessage(value);

    // Auto-resize
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }, []);

  // Quick message suggestions
  const quickMessages = [
    "Analyze my portfolio allocation",
    "What are the expense ratios?", 
    "Show me fund performance data",
    "Get fund recommendations"
  ];

  const handleQuickMessage = useCallback((quickMessage: string) => {
    if (canSend && !isTyping) {
      onSendMessage(quickMessage);
    }
  }, [canSend, isTyping, onSendMessage]);

  return (
    <div className={cn("space-y-3", className)}>
      {/* Quick Messages (shown when input is empty) */}
      {message.length === 0 && (
        <div className="flex flex-wrap gap-2">
          {quickMessages.map((quickMessage, index) => (
            <button
              key={index}
              onClick={() => handleQuickMessage(quickMessage)}
              disabled={!canSend || isTyping}
              className={cn(
                "px-3 py-1 text-xs rounded-full border transition-colors",
                canSend && !isTyping
                  ? "text-gray-600 border-gray-300 hover:bg-gray-50 hover:border-gray-400"
                  : "text-gray-400 border-gray-200 cursor-not-allowed"
              )}
            >
              {quickMessage}
            </button>
          ))}
        </div>
      )}

      {/* Main Input Area */}
      <div className="flex items-end space-x-3">
        {/* File Upload Button */}
        <button
          onClick={onUploadFile}
          disabled={!canUpload || isTyping}
          className={cn(
            "p-2 rounded-full transition-colors",
            canUpload && !isTyping
              ? "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
              : "text-gray-300 cursor-not-allowed"
          )}
          title="Upload file"
        >
          <Paperclip className="h-5 w-5" />
        </button>

        {/* Message Input */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            disabled={!canSend || isTyping}
            placeholder={isTyping ? "Please wait..." : placeholder}
            className={cn(
              "w-full px-4 py-2 border border-gray-300 rounded-lg resize-none transition-colors",
              "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
              "disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed",
              "min-h-[40px] max-h-[120px]"
            )}
            rows={1}
          />
          
          {/* Character Count (optional, shown when approaching limit) */}
          {message.length > 800 && (
            <div className="absolute bottom-1 right-2 text-xs text-gray-400">
              {message.length}/1000
            </div>
          )}
        </div>

        {/* Send Button */}
        <button
          onClick={handleSend}
          disabled={!canSend || !message.trim() || isTyping}
          className={cn(
            "p-2 rounded-full transition-all duration-200",
            canSend && message.trim() && !isTyping
              ? "bg-blue-600 text-white hover:bg-blue-700 shadow-md"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          )}
          title={isTyping ? "Please wait..." : "Send message"}
        >
          {isTyping ? (
            <Loader className="h-5 w-5 animate-spin" />
          ) : (
            <Send className="h-5 w-5" />
          )}
        </button>
      </div>

      {/* Input Help Text */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center space-x-4">
          <span>Press Enter to send, Shift+Enter for new line</span>
          {canUpload && (
            <span>• Click 📎 to upload files</span>
          )}
        </div>
        
        {isTyping && (
          <div className="flex items-center space-x-1">
            <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            <span className="ml-2">Assistant is thinking...</span>
          </div>
        )}
      </div>
    </div>
  );
}
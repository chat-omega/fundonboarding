"use client";

import { useMemo } from 'react';
import { format } from 'date-fns';
import { 
  User, 
  Bot, 
  Settings,
  FileText,
  Upload,
  CheckCircle,
  AlertCircle,
  Info,
  TrendingUp,
  BarChart3,
  Clock
} from 'lucide-react';
import { ChatMessage, PortfolioItem, FundExtraction } from '@/lib/chat-types';
import { cn } from '@/lib/utils';

interface MessageListProps {
  messages: ChatMessage[];
  isTyping?: boolean;
  portfolioData?: PortfolioItem[];
  fundExtractions?: Record<string, FundExtraction>;
  className?: string;
}

export function MessageList({ 
  messages, 
  isTyping, 
  portfolioData = [], 
  fundExtractions = {},
  className 
}: MessageListProps) {
  // Format message content with markdown support
  const formatMessageContent = (content: string, type?: string) => {
    if (type === 'fund_data' || type === 'portfolio_summary') {
      // For structured data, format as JSON or table
      try {
        const data = JSON.parse(content);
        return (
          <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto">
            {JSON.stringify(data, null, 2)}
          </pre>
        );
      } catch {
        return content;
      }
    }

    // Basic markdown-like formatting
    return content
      .split('\n')
      .map((line, i) => {
        // Headers
        if (line.startsWith('# ')) {
          return <h3 key={i} className="text-lg font-bold mt-4 mb-2">{line.slice(2)}</h3>;
        }
        if (line.startsWith('## ')) {
          return <h4 key={i} className="text-base font-semibold mt-3 mb-2">{line.slice(3)}</h4>;
        }
        
        // Bold text
        const boldText = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Lists
        if (line.startsWith('- ')) {
          return (
            <li key={i} className="ml-4 mb-1">
              <span dangerouslySetInnerHTML={{ __html: boldText.slice(2) }} />
            </li>
          );
        }
        
        // Regular paragraphs
        if (line.trim()) {
          return (
            <p key={i} className="mb-2">
              <span dangerouslySetInnerHTML={{ __html: boldText }} />
            </p>
          );
        }
        
        return <br key={i} />;
      });
  };

  // Get message icon based on role and type
  const getMessageIcon = (message: ChatMessage) => {
    switch (message.role) {
      case 'user':
        if (message.type === 'file_upload') {
          return <Upload className="h-4 w-4" />;
        }
        return <User className="h-4 w-4" />;
      
      case 'assistant':
        if (message.type === 'fund_data') {
          return <TrendingUp className="h-4 w-4" />;
        }
        if (message.type === 'portfolio_summary') {
          return <BarChart3 className="h-4 w-4" />;
        }
        return <Bot className="h-4 w-4" />;
      
      case 'system':
        if (message.type === 'error') {
          return <AlertCircle className="h-4 w-4" />;
        }
        if (message.type === 'status') {
          return <Info className="h-4 w-4" />;
        }
        return <Settings className="h-4 w-4" />;
      
      default:
        return <Settings className="h-4 w-4" />;
    }
  };

  // Get message styling based on role and type
  const getMessageStyling = (message: ChatMessage) => {
    const baseClasses = "flex items-start space-x-3 p-4";
    
    switch (message.role) {
      case 'user':
        return {
          container: cn(baseClasses, "bg-blue-50 border-l-4 border-blue-400"),
          icon: "text-blue-600 bg-blue-100 p-2 rounded-full",
          content: "flex-1"
        };
      
      case 'assistant':
        return {
          container: cn(baseClasses, "bg-green-50 border-l-4 border-green-400"),
          icon: "text-green-600 bg-green-100 p-2 rounded-full",
          content: "flex-1"
        };
      
      case 'system':
        if (message.type === 'error') {
          return {
            container: cn(baseClasses, "bg-red-50 border-l-4 border-red-400"),
            icon: "text-red-600 bg-red-100 p-2 rounded-full",
            content: "flex-1"
          };
        }
        return {
          container: cn(baseClasses, "bg-gray-50 border-l-4 border-gray-400"),
          icon: "text-gray-600 bg-gray-100 p-2 rounded-full",
          content: "flex-1"
        };
      
      default:
        return {
          container: cn(baseClasses, "bg-gray-50"),
          icon: "text-gray-600 bg-gray-100 p-2 rounded-full",
          content: "flex-1"
        };
    }
  };

  // Generate portfolio summary for display
  const portfolioSummaryMessage = useMemo(() => {
    if (portfolioData.length === 0) return null;

    const totalFunds = portfolioData.length;
    const avgConfidence = portfolioData.reduce((sum, item) => sum + item.confidence_score, 0) / totalFunds;
    const assetClasses = [...new Set(portfolioData.map(item => item.asset_class))];
    
    return {
      id: 'portfolio-summary',
      role: 'assistant' as const,
      content: `📊 **Portfolio Summary**

**Total Holdings:** ${totalFunds} funds
**Asset Classes:** ${assetClasses.join(', ')}
**Average Confidence:** ${Math.round(avgConfidence * 100)}%

**Top Holdings:**
${portfolioData.slice(0, 5).map(item => 
  `- **${item.ticker}** - ${item.name} (${item.asset_class})`
).join('\n')}`,
      timestamp: new Date(),
      type: 'portfolio_summary' as const,
      metadata: { fund_count: totalFunds }
    };
  }, [portfolioData]);

  // Generate fund extractions summary
  const fundExtractionsMessage = useMemo(() => {
    const extractionCount = Object.keys(fundExtractions).length;
    if (extractionCount === 0) return null;

    const avgConfidence = Object.values(fundExtractions)
      .reduce((sum, fund) => sum + fund.confidence_score, 0) / extractionCount;

    return {
      id: 'fund-extractions-summary',
      role: 'assistant' as const,
      content: `💰 **Fund Data Extraction Complete**

**Extracted:** ${extractionCount} fund profiles
**Average Confidence:** ${Math.round(avgConfidence * 100)}%

**Extracted Funds:**
${Object.entries(fundExtractions).slice(0, 5).map(([ticker, fund]) => 
  `- **${ticker}** - ${fund.fund_name || 'Unknown'} (${Math.round(fund.confidence_score * 100)}%)`
).join('\n')}`,
      timestamp: new Date(),
      type: 'fund_data' as const,
      metadata: { extraction_count: extractionCount }
    };
  }, [fundExtractions]);

  // Combine all messages with auto-generated summaries
  const allMessages = useMemo(() => {
    const result = [...messages];
    
    // Add portfolio summary after portfolio processing
    if (portfolioSummaryMessage && !messages.some(m => m.type === 'portfolio_summary')) {
      const lastPortfolioMessage = messages.findLast(m => 
        m.content.includes('portfolio') && m.role === 'system'
      );
      if (lastPortfolioMessage) {
        const insertIndex = messages.indexOf(lastPortfolioMessage) + 1;
        result.splice(insertIndex, 0, portfolioSummaryMessage);
      }
    }
    
    // Add fund extractions summary after extraction completion
    if (fundExtractionsMessage && !messages.some(m => m.type === 'fund_data' && m.metadata?.extraction_count)) {
      const lastExtractionMessage = messages.findLast(m => 
        m.content.includes('Analysis complete') && m.role === 'system'
      );
      if (lastExtractionMessage) {
        const insertIndex = messages.indexOf(lastExtractionMessage) + 1;
        result.splice(insertIndex, 0, fundExtractionsMessage);
      }
    }
    
    return result;
  }, [messages, portfolioSummaryMessage, fundExtractionsMessage]);

  return (
    <div className={cn("space-y-1", className)}>
      {allMessages.map((message) => {
        const styling = getMessageStyling(message);
        const icon = getMessageIcon(message);
        
        return (
          <div key={message.id} className={styling.container}>
            <div className={styling.icon}>
              {icon}
            </div>
            
            <div className={styling.content}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium capitalize text-gray-900">
                    {message.role}
                  </span>
                  {message.type && message.type !== 'text' && (
                    <span className="text-xs px-2 py-1 bg-gray-200 rounded-full text-gray-600">
                      {message.type.replace('_', ' ')}
                    </span>
                  )}
                </div>
                
                <div className="flex items-center space-x-2 text-xs text-gray-500">
                  {message.metadata?.progress !== undefined && (
                    <div className="flex items-center space-x-1">
                      <div className="w-16 bg-gray-200 rounded-full h-1">
                        <div 
                          className="bg-blue-600 h-1 rounded-full transition-all duration-300"
                          style={{ width: `${message.metadata.progress * 100}%` }}
                        />
                      </div>
                      <span>{Math.round(message.metadata.progress * 100)}%</span>
                    </div>
                  )}
                  
                  <div className="flex items-center space-x-1">
                    <Clock className="h-3 w-3" />
                    <span>{format(message.timestamp, 'HH:mm')}</span>
                  </div>
                </div>
              </div>
              
              <div className="text-sm text-gray-800 prose prose-sm max-w-none">
                {formatMessageContent(message.content, message.type)}
              </div>
              
              {/* File Upload Metadata */}
              {message.type === 'file_upload' && message.metadata && (
                <div className="mt-2 p-2 bg-gray-100 rounded text-xs">
                  <div className="flex items-center justify-between">
                    <span>📁 {message.metadata.file_name}</span>
                    <span>{message.metadata.file_size ? 
                      `${(message.metadata.file_size / 1024).toFixed(1)} KB` : 
                      ''
                    }</span>
                  </div>
                </div>
              )}
              
              {/* Confidence Score */}
              {message.metadata?.confidence !== undefined && (
                <div className="mt-2 flex items-center space-x-2 text-xs text-gray-600">
                  <span>Confidence:</span>
                  <div className="flex items-center space-x-1">
                    <div className="w-12 bg-gray-200 rounded-full h-1">
                      <div 
                        className={cn(
                          "h-1 rounded-full",
                          message.metadata.confidence >= 0.8 ? "bg-green-500" :
                          message.metadata.confidence >= 0.6 ? "bg-yellow-500" : "bg-red-500"
                        )}
                        style={{ width: `${message.metadata.confidence * 100}%` }}
                      />
                    </div>
                    <span>{Math.round(message.metadata.confidence * 100)}%</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
      
      {/* Typing Indicator */}
      {isTyping && (
        <div className="flex items-start space-x-3 p-4 bg-green-50 border-l-4 border-green-400">
          <div className="text-green-600 bg-green-100 p-2 rounded-full">
            <Bot className="h-4 w-4" />
          </div>
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-sm font-medium text-gray-900">Assistant</span>
              <span className="text-xs px-2 py-1 bg-gray-200 rounded-full text-gray-600">
                typing
              </span>
            </div>
            <div className="flex items-center space-x-1 text-sm text-gray-600">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span>Processing your request...</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
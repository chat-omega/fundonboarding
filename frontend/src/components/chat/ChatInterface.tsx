"use client";

import { useState, useCallback, useRef, useEffect } from 'react';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { FileUploadWidget } from './FileUploadWidget';
import { StreamingIndicator } from './StreamingIndicator';
import { FundCard } from './FundCard';
import { PortfolioSummary } from './PortfolioSummary';
import { CategoryQuestionWidget } from './CategoryQuestionWidget';
import { FundCategorizationTable } from './FundCategorizationTable';
import { CategorizationSummary } from './CategorizationSummary';
import { useChat } from '@/hooks/useChat';
import { useSSE } from '@/hooks/useSSE';
import { 
  ChatMessage, 
  AgentMessage,
  OnboardingStage,
  QuickAction,
  PortfolioItem,
  FundExtraction,
  CategoryQuestion,
  CategoryResponse,
  FundCategorization
} from '@/lib/chat-types';
import { cn } from '@/lib/utils';
import { 
  FileText, 
  BarChart3, 
  Loader, 
  CheckCircle, 
  AlertCircle,
  Upload,
  MessageSquare,
  TrendingUp,
  Tags
} from 'lucide-react';

interface ChatInterfaceProps {
  sessionId?: string;
  className?: string;
}

export function ChatInterface({ sessionId, className }: ChatInterfaceProps) {
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [portfolioData, setPortfolioData] = useState<PortfolioItem[]>([]);
  const [fundExtractions, setFundExtractions] = useState<Record<string, FundExtraction>>({});
  const [currentStage, setCurrentStage] = useState<OnboardingStage>('greeting');
  const [currentQuestion, setCurrentQuestion] = useState<CategoryQuestion | null>(null);
  const [categorizations, setCategorizations] = useState<FundCategorization[]>([]);
  const [showCategorizationTable, setShowCategorizationTable] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    session,
    messages,
    isLoading,
    isConnected,
    error,
    isTyping,
    sessionId: activeSessionId,
    sendMessage,
    uploadFile,
    addSystemMessage,
    canUpload,
    canSendMessage
  } = useChat({ sessionId, autoCreateSession: !sessionId });

  // SSE connection for real-time updates
  const {
    isConnected: sseConnected,
    connectionStatus,
    lastMessage
  } = useSSE(activeSessionId, {
    onMessage: (message: AgentMessage) => {
      console.log('Received SSE message:', message);
      handleSSEMessage(message);
    },
    onStatusUpdate: (data: any) => {
      addSystemMessage(
        `${data.stage || 'Processing'}: ${data.message || 'Working on your request...'}`,
        'status',
        data
      );
      if (data.stage) {
        setCurrentStage(data.stage);
      }
    },
    onPortfolioProcessed: (data: any) => {
      if (data.portfolio_items) {
        setPortfolioData(data.portfolio_items);
        addSystemMessage(
          `📊 Portfolio processed! Found ${data.portfolio_items.length} fund holdings.`,
          'success',
          data
        );
      }
    },
    onFundExtracted: (data: any) => {
      if (data.ticker) {
        addSystemMessage(
          `💰 Extracted data for ${data.fund_name || data.ticker} (${Math.round((data.confidence || 0) * 100)}% confidence)`,
          'success',
          data
        );
      }
    },
    onAnalysisComplete: (data: any) => {
      if (data.fund_extractions) {
        setFundExtractions(data.fund_extractions);
        addSystemMessage(
          `🎉 Analysis complete! Successfully extracted ${Object.keys(data.fund_extractions).length} fund profiles.`,
          'success',
          data
        );
      }
    },
    onCategorizationQuestion: (data: any) => {
      if (data.question) {
        setCurrentQuestion(data.question);
        addSystemMessage(
          `📊 Please help categorize fund: ${data.question.context.fund_name || data.question.context.fund_ticker}`,
          'status',
          data
        );
      }
    },
    onCategorizationComplete: (data: any) => {
      if (data.categorizations) {
        setCategorizations(data.categorizations);
        setShowCategorizationTable(true);
        setCurrentQuestion(null);
        addSystemMessage(
          `✅ Fund categorization complete! Review ${data.categorizations.length} categorized funds.`,
          'success',
          data
        );
      }
    }
  });

  // Handle SSE messages
  const handleSSEMessage = useCallback((message: AgentMessage) => {
    switch (message.type) {
      case 'connected':
        console.log('SSE connected for session:', message.data.session_id);
        break;
        
      case 'status':
        if (message.data.stage) {
          setCurrentStage(message.data.stage as OnboardingStage);
        }
        break;
        
      case 'portfolio_processed':
        if (message.data.portfolio_items) {
          setPortfolioData(message.data.portfolio_items);
        }
        break;
        
      case 'fund_extracted':
        // Individual fund extraction completed
        break;
        
      case 'analysis_complete':
        if (message.data.fund_extractions) {
          setFundExtractions(message.data.fund_extractions);
        }
        break;
        
      case 'chat_response':
        // Handle direct chat responses
        break;
        
      case 'categorization_question':
        if (message.data.question) {
          setCurrentQuestion(message.data.question);
        }
        break;
        
      case 'categorization_complete':
        if (message.data.categorizations) {
          setCategorizations(message.data.categorizations);
          setShowCategorizationTable(true);
          setCurrentQuestion(null);
        }
        break;
    }
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Handle file upload
  const handleFileUpload = useCallback(async (file: File) => {
    setShowUploadDialog(false);
    await uploadFile(file);
  }, [uploadFile]);

  // Handle message send
  const handleSendMessage = useCallback(async (content: string) => {
    await sendMessage(content);
  }, [sendMessage]);

  // Handle category question response
  const handleCategoryResponse = useCallback(async (response: CategoryResponse) => {
    await sendMessage(`CATEGORY_RESPONSE:${JSON.stringify(response)}`);
    setCurrentQuestion(null);
  }, [sendMessage]);

  // Handle categorization table interactions
  const handleEditCategorization = useCallback(async (categorizationId: string, newCategory: any, reason: string) => {
    await sendMessage(`UPDATE_CATEGORIZATION:${JSON.stringify({ 
      categorization_id: categorizationId, 
      new_category: newCategory, 
      reason 
    })}`);
  }, [sendMessage]);

  const handleApproveCategorization = useCallback(async (categorizationId: string) => {
    await sendMessage(`APPROVE_CATEGORIZATION:${categorizationId}`);
  }, [sendMessage]);

  const handleBulkApproveCategorizations = useCallback(async (categorizationIds: string[]) => {
    await sendMessage(`BULK_APPROVE_CATEGORIZATIONS:${JSON.stringify(categorizationIds)}`);
  }, [sendMessage]);

  // Quick actions
  const quickActions: QuickAction[] = [
    {
      id: 'upload_csv',
      label: 'Upload Portfolio CSV',
      action: 'upload_csv',
      icon: 'FileText',
      enabled: canUpload && currentStage === 'greeting'
    },
    {
      id: 'upload_pdf',
      label: 'Upload Fund PDF',
      action: 'upload_pdf', 
      icon: 'Upload',
      enabled: canUpload
    },
    {
      id: 'analyze_portfolio',
      label: 'Analyze Portfolio',
      action: 'analyze_portfolio',
      icon: 'BarChart3',
      enabled: portfolioData.length > 0
    },
    {
      id: 'start_categorization',
      label: 'Categorize Funds',
      action: 'start_categorization',
      icon: 'Tags',
      enabled: portfolioData.length > 0 && ['analysis', 'complete'].includes(currentStage)
    },
    {
      id: 'get_recommendations',
      label: 'Get Recommendations',
      action: 'get_recommendations',
      icon: 'TrendingUp',
      enabled: Object.keys(fundExtractions).length > 0 || categorizations.length > 0
    }
  ];

  const handleQuickAction = useCallback(async (action: QuickAction) => {
    switch (action.action) {
      case 'upload_csv':
      case 'upload_pdf':
        setShowUploadDialog(true);
        break;
        
      case 'analyze_portfolio':
        await sendMessage('Please analyze my portfolio and provide insights on asset allocation and risk distribution.');
        break;
        
      case 'start_categorization':
        await sendMessage('Please start the fund categorization process for my portfolio.');
        break;
        
      case 'get_recommendations':
        await sendMessage('Based on the fund data you\'ve extracted, what recommendations do you have for my portfolio?');
        break;
    }
  }, [sendMessage]);

  return (
    <div className={cn("flex h-screen bg-gray-50", className)}>
      {/* Main Chat Panel */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 p-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <MessageSquare className="h-6 w-6 text-blue-600" />
              <h1 className="text-lg font-semibold text-gray-900">Fund Onboarding</h1>
            </div>
            {activeSessionId && (
              <span className="text-xs text-gray-500 font-mono">
                Session: {activeSessionId.slice(0, 8)}...
              </span>
            )}
          </div>
          
          <div className="flex items-center space-x-3">
            {/* Connection Status */}
            <div className="flex items-center space-x-2">
              <div className={cn(
                "w-2 h-2 rounded-full",
                sseConnected ? "bg-green-500" : "bg-red-500"
              )} />
              <span className="text-xs text-gray-600">
                {sseConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            
            {/* Current Stage */}
            <div className="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded">
              Stage: {currentStage}
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto">
          <MessageList 
            messages={messages}
            isTyping={isTyping}
            portfolioData={portfolioData}
            fundExtractions={fundExtractions}
          />
          
          {/* Category Question Widget */}
          {currentQuestion && (
            <div className="p-4">
              <CategoryQuestionWidget
                question={currentQuestion}
                onResponse={handleCategoryResponse}
                disabled={isLoading}
              />
            </div>
          )}
          
          {/* Fund Categorization Table */}
          {showCategorizationTable && categorizations.length > 0 && (
            <div className="p-4">
              <FundCategorizationTable
                categorizations={categorizations}
                onEdit={handleEditCategorization}
                onApprove={handleApproveCategorization}
                onBulkApprove={handleBulkApproveCategorizations}
              />
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Actions */}
        {quickActions.some(action => action.enabled) && (
          <div className="bg-white border-t border-gray-200 p-3">
            <div className="flex flex-wrap gap-2">
              {quickActions
                .filter(action => action.enabled)
                .map((action) => (
                  <button
                    key={action.id}
                    onClick={() => handleQuickAction(action)}
                    className="flex items-center space-x-2 px-3 py-2 text-sm text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
                  >
                    {action.icon === 'FileText' && <FileText className="h-4 w-4" />}
                    {action.icon === 'Upload' && <Upload className="h-4 w-4" />}
                    {action.icon === 'BarChart3' && <BarChart3 className="h-4 w-4" />}
                    {action.icon === 'Tags' && <Tags className="h-4 w-4" />}
                    {action.icon === 'TrendingUp' && <TrendingUp className="h-4 w-4" />}
                    <span>{action.label}</span>
                  </button>
                ))}
            </div>
          </div>
        )}

        {/* Message Input */}
        <div className="bg-white border-t border-gray-200 p-4">
          <MessageInput
            onSendMessage={handleSendMessage}
            onUploadFile={() => setShowUploadDialog(true)}
            canSend={canSendMessage}
            canUpload={canUpload}
            isTyping={isTyping}
          />
        </div>
        
        {/* Streaming Indicator */}
        {(isLoading || isTyping || connectionStatus === 'connecting') && (
          <StreamingIndicator 
            isVisible={true}
            stage={currentStage}
            message={isLoading ? "Loading..." : isTyping ? "Processing your message..." : "Connecting..."}
          />
        )}
      </div>

      {/* Right Panel - Data Visualization */}
      <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Data Overview</h2>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Portfolio Summary */}
          {portfolioData.length > 0 && (
            <PortfolioSummary 
              portfolioItems={portfolioData}
              className="mb-4"
            />
          )}

          {/* Categorization Summary */}
          {categorizations.length > 0 && (
            <CategorizationSummary
              categorizations={categorizations}
              className="mb-4"
            />
          )}
          
          {/* Fund Cards */}
          {Object.entries(fundExtractions).map(([ticker, fund]) => (
            <FundCard
              key={ticker}
              ticker={ticker}
              fundData={fund}
              className="mb-3"
            />
          ))}
          
          {/* Empty State */}
          {portfolioData.length === 0 && Object.keys(fundExtractions).length === 0 && categorizations.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <BarChart3 className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p className="text-sm">
                Upload files to see your portfolio analysis and fund data here.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* File Upload Dialog */}
      {showUploadDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96 max-w-90vw">
            <FileUploadWidget
              onUpload={handleFileUpload}
              onCancel={() => setShowUploadDialog(false)}
              acceptedTypes={{
                'text/csv': ['.csv'],
                'application/vnd.ms-excel': ['.xls'],
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
                'application/pdf': ['.pdf']
              }}
            />
          </div>
        </div>
      )}
      
      {/* Error Display */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded shadow-lg z-50">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-5 w-5" />
            <span>{error}</span>
          </div>
        </div>
      )}
    </div>
  );
}
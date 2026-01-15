"use client";

import { useEffect, useState } from 'react';
import { Loader, Wifi, WifiOff, CheckCircle, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { OnboardingStage } from '@/lib/chat-types';

interface StreamingIndicatorProps {
  isVisible: boolean;
  stage?: OnboardingStage;
  message?: string;
  progress?: number;
  isConnected?: boolean;
  className?: string;
}

export function StreamingIndicator({
  isVisible,
  stage,
  message,
  progress,
  isConnected = true,
  className
}: StreamingIndicatorProps) {
  const [dots, setDots] = useState('');

  // Animate dots
  useEffect(() => {
    if (!isVisible) return;

    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 500);

    return () => clearInterval(interval);
  }, [isVisible]);

  // Get stage-specific content
  const getStageContent = (stage?: OnboardingStage) => {
    switch (stage) {
      case 'greeting':
        return {
          icon: <Loader className="h-4 w-4 animate-spin" />,
          title: 'Getting Ready',
          description: 'Initializing your session...'
        };
      
      case 'file_upload':
        return {
          icon: <Loader className="h-4 w-4 animate-spin" />,
          title: 'Processing Upload',
          description: 'Analyzing your file...'
        };
      
      case 'processing':
        return {
          icon: <Loader className="h-4 w-4 animate-spin" />,
          title: 'Processing Data',
          description: 'Parsing portfolio holdings...'
        };
      
      case 'research':
        return {
          icon: <Loader className="h-4 w-4 animate-spin" />,
          title: 'Researching Funds',
          description: 'Finding fund prospectuses...'
        };
      
      case 'extraction':
        return {
          icon: <Loader className="h-4 w-4 animate-spin" />,
          title: 'Extracting Data',
          description: 'Analyzing fund documents...'
        };
      
      case 'analysis':
        return {
          icon: <Loader className="h-4 w-4 animate-spin" />,
          title: 'Analyzing Portfolio',
          description: 'Generating insights...'
        };
      
      case 'recommendations':
        return {
          icon: <Loader className="h-4 w-4 animate-spin" />,
          title: 'Generating Recommendations',
          description: 'Preparing your report...'
        };
      
      case 'complete':
        return {
          icon: <CheckCircle className="h-4 w-4 text-green-500" />,
          title: 'Complete',
          description: 'Analysis finished!'
        };
      
      default:
        return {
          icon: <Loader className="h-4 w-4 animate-spin" />,
          title: 'Working',
          description: 'Processing your request...'
        };
    }
  };

  if (!isVisible) return null;

  const stageContent = getStageContent(stage);

  return (
    <div className={cn(
      "fixed bottom-20 right-4 bg-white border border-gray-200 rounded-lg shadow-lg p-4 min-w-[280px] max-w-[320px] z-50",
      "animate-in slide-in-from-right-full duration-300",
      className
    )}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          {stageContent.icon}
          <span className="text-sm font-medium text-gray-900">
            {stageContent.title}
          </span>
        </div>
        
        {/* Connection Status */}
        <div className="flex items-center space-x-1">
          {isConnected ? (
            <Wifi className="h-3 w-3 text-green-500" />
          ) : (
            <WifiOff className="h-3 w-3 text-red-500" />
          )}
          <span className={cn(
            "text-xs",
            isConnected ? "text-green-600" : "text-red-600"
          )}>
            {isConnected ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      {progress !== undefined && (
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-600">Progress</span>
            <span className="text-xs text-gray-600">{Math.round(progress * 100)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-1.5">
            <div 
              className="bg-blue-600 h-1.5 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Message */}
      <div className="text-sm text-gray-600">
        {message || stageContent.description}
        <span className="inline-block w-3">{dots}</span>
      </div>

      {/* Stage-specific Additional Info */}
      {stage === 'extraction' && (
        <div className="mt-2 text-xs text-gray-500">
          <div className="flex items-center space-x-1">
            <div className="w-1 h-1 bg-blue-500 rounded-full animate-pulse" />
            <span>Using AI to extract fund data</span>
          </div>
        </div>
      )}

      {stage === 'research' && (
        <div className="mt-2 text-xs text-gray-500">
          <div className="flex items-center space-x-1">
            <div className="w-1 h-1 bg-blue-500 rounded-full animate-pulse" />
            <span>Searching web for fund documents</span>
          </div>
        </div>
      )}

      {stage === 'analysis' && (
        <div className="mt-2 text-xs text-gray-500">
          <div className="flex items-center space-x-1">
            <div className="w-1 h-1 bg-blue-500 rounded-full animate-pulse" />
            <span>Calculating risk metrics</span>
          </div>
        </div>
      )}

      {/* Activity Indicator */}
      <div className="mt-3 flex items-center justify-center space-x-1">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="w-1 h-1 bg-blue-500 rounded-full animate-bounce"
            style={{ 
              animationDelay: `${i * 150}ms`,
              animationDuration: '1s'
            }}
          />
        ))}
      </div>
    </div>
  );
}
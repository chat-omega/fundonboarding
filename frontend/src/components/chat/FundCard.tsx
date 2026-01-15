"use client";

import { useState } from 'react';
import { ChevronDown, ChevronUp, TrendingUp, TrendingDown, DollarSign, Percent, Calendar, Award } from 'lucide-react';
import { FundExtraction } from '@/lib/chat-types';
import { cn } from '@/lib/utils';

interface FundCardProps {
  ticker: string;
  fundData: FundExtraction;
  className?: string;
}

export function FundCard({ ticker, fundData, className }: FundCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Format currency values
  const formatCurrency = (value: number | undefined) => {
    if (value === undefined || value === null) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  // Format percentage values
  const formatPercent = (value: number | undefined) => {
    if (value === undefined || value === null) return 'N/A';
    return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  // Get confidence color
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 bg-green-100';
    if (confidence >= 0.6) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  // Get return color
  const getReturnColor = (returnValue: number | undefined) => {
    if (returnValue === undefined || returnValue === null) return 'text-gray-500';
    return returnValue >= 0 ? 'text-green-600' : 'text-red-600';
  };

  return (
    <div className={cn(
      "bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow",
      className
    )}>
      {/* Card Header */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{ticker}</h3>
            <p className="text-sm text-gray-600 truncate">
              {fundData.fund_name || 'Unknown Fund'}
            </p>
          </div>
          
          {/* Confidence Badge */}
          <div className={cn(
            "px-2 py-1 rounded-full text-xs font-medium",
            getConfidenceColor(fundData.confidence_score)
          )}>
            {Math.round(fundData.confidence_score * 100)}% confidence
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 gap-4 mb-3">
          {/* NAV */}
          {fundData.nav && (
            <div className="flex items-center space-x-2">
              <DollarSign className="h-4 w-4 text-gray-400" />
              <div>
                <p className="text-xs text-gray-500">NAV</p>
                <p className="text-sm font-medium">{formatCurrency(fundData.nav)}</p>
              </div>
            </div>
          )}

          {/* Expense Ratio */}
          {fundData.expense_ratio && (
            <div className="flex items-center space-x-2">
              <Percent className="h-4 w-4 text-gray-400" />
              <div>
                <p className="text-xs text-gray-500">Expense Ratio</p>
                <p className="text-sm font-medium">{fundData.expense_ratio}%</p>
              </div>
            </div>
          )}

          {/* 1-Year Return */}
          {fundData.one_year_return !== undefined && (
            <div className="flex items-center space-x-2">
              {fundData.one_year_return >= 0 ? (
                <TrendingUp className="h-4 w-4 text-green-500" />
              ) : (
                <TrendingDown className="h-4 w-4 text-red-500" />
              )}
              <div>
                <p className="text-xs text-gray-500">1-Year Return</p>
                <p className={cn(
                  "text-sm font-medium",
                  getReturnColor(fundData.one_year_return)
                )}>
                  {formatPercent(fundData.one_year_return)}
                </p>
              </div>
            </div>
          )}

          {/* Data Source */}
          <div className="flex items-center space-x-2">
            <Award className="h-4 w-4 text-gray-400" />
            <div>
              <p className="text-xs text-gray-500">Source</p>
              <p className="text-sm font-medium capitalize">{fundData.data_source}</p>
            </div>
          </div>
        </div>

        {/* Expand Button */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-700"
        >
          <span>{isExpanded ? 'Less Details' : 'More Details'}</span>
          {isExpanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="border-t border-gray-200 p-4">
          <div className="space-y-4">
            {/* Extraction Metadata */}
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-2">Extraction Details</h4>
              <div className="grid grid-cols-2 gap-3 text-xs text-gray-600">
                <div>
                  <span className="font-medium">Method:</span> {fundData.extraction_method}
                </div>
                <div>
                  <span className="font-medium">Processing Time:</span> {
                    fundData.processing_time ? 
                    `${fundData.processing_time.toFixed(2)}s` : 
                    'N/A'
                  }
                </div>
                <div>
                  <span className="font-medium">Extracted:</span> {
                    new Date(fundData.extracted_at).toLocaleString()
                  }
                </div>
                <div>
                  <span className="font-medium">Source Document:</span> {
                    fundData.source_document ? 
                    'Available' : 
                    'N/A'
                  }
                </div>
              </div>
            </div>

            {/* All Available Data */}
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-2">All Extracted Fields</h4>
              <div className="bg-gray-50 p-3 rounded text-xs">
                <div className="grid grid-cols-1 gap-2">
                  {Object.entries(fundData).map(([key, value]) => {
                    // Skip metadata fields
                    if (['ticker', 'confidence_score', 'extraction_method', 'processing_time', 'data_source', 'extracted_at', 'source_document'].includes(key)) {
                      return null;
                    }

                    // Skip null/undefined values
                    if (value === null || value === undefined || value === '') {
                      return null;
                    }

                    // Format field name
                    const fieldName = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    
                    // Format value
                    let formattedValue = value;
                    if (typeof value === 'number') {
                      if (key.includes('ratio') || key.includes('return') || key.includes('pct')) {
                        formattedValue = `${value}%`;
                      } else if (key.includes('nav') || key.includes('assets') || key.includes('income')) {
                        formattedValue = formatCurrency(value);
                      } else {
                        formattedValue = value.toLocaleString();
                      }
                    }

                    return (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-600">{fieldName}:</span>
                        <span className="text-gray-900 font-medium">{formattedValue}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Quality Indicators */}
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-2">Data Quality</h4>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-600">Extraction Confidence</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-16 bg-gray-200 rounded-full h-1">
                      <div 
                        className={cn(
                          "h-1 rounded-full",
                          fundData.confidence_score >= 0.8 ? "bg-green-500" :
                          fundData.confidence_score >= 0.6 ? "bg-yellow-500" : "bg-red-500"
                        )}
                        style={{ width: `${fundData.confidence_score * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-600">
                      {Math.round(fundData.confidence_score * 100)}%
                    </span>
                  </div>
                </div>

                {/* Field Completeness */}
                {(() => {
                  const totalFields = Object.keys(fundData).length;
                  const filledFields = Object.values(fundData).filter(v => v !== null && v !== undefined && v !== '').length;
                  const completeness = filledFields / totalFields;
                  
                  return (
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-600">Data Completeness</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-gray-200 rounded-full h-1">
                          <div 
                            className="bg-blue-500 h-1 rounded-full"
                            style={{ width: `${completeness * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-600">
                          {Math.round(completeness * 100)}%
                        </span>
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
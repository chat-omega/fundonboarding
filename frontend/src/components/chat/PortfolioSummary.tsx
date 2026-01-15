"use client";

import { useMemo } from 'react';
import { PortfolioItem } from '@/lib/chat-types';
import { cn } from '@/lib/utils';
import { TrendingUp, Shield, Target, AlertTriangle, Award, PieChart } from 'lucide-react';

interface PortfolioSummaryProps {
  portfolioItems: PortfolioItem[];
  className?: string;
}

export function PortfolioSummary({ portfolioItems, className }: PortfolioSummaryProps) {
  // Calculate portfolio metrics
  const portfolioMetrics = useMemo(() => {
    if (!portfolioItems.length) return null;

    // Asset class distribution
    const assetClassDistribution = portfolioItems.reduce((acc, item) => {
      const assetClass = item.asset_class || 'Unknown';
      acc[assetClass] = (acc[assetClass] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    // Risk profile distribution
    const riskDistribution = {
      conservative: portfolioItems.reduce((sum, item) => sum + (item.conservative_pct || 0), 0),
      mod_conservative: portfolioItems.reduce((sum, item) => sum + (item.mod_conservative_pct || 0), 0),
      moderate: portfolioItems.reduce((sum, item) => sum + (item.moderate_pct || 0), 0),
      growth: portfolioItems.reduce((sum, item) => sum + (item.growth_pct || 0), 0),
      aggressive: portfolioItems.reduce((sum, item) => sum + (item.aggressive_pct || 0), 0),
    };

    // Quality metrics
    const avgConfidence = portfolioItems.reduce((sum, item) => sum + item.confidence_score, 0) / portfolioItems.length;
    const lowConfidenceCount = portfolioItems.filter(item => item.confidence_score < 0.7).length;
    const needsProspectus = portfolioItems.filter(item => item.requires_prospectus).length;
    const avgExpenseRatio = portfolioItems
      .filter(item => item.expense_ratio && item.expense_ratio > 0)
      .reduce((sum, item) => sum + (item.expense_ratio || 0), 0) / 
      portfolioItems.filter(item => item.expense_ratio && item.expense_ratio > 0).length;

    return {
      totalFunds: portfolioItems.length,
      uniqueAssetClasses: Object.keys(assetClassDistribution).length,
      assetClassDistribution,
      riskDistribution,
      avgConfidence,
      lowConfidenceCount,
      needsProspectus,
      avgExpenseRatio: isNaN(avgExpenseRatio) ? null : avgExpenseRatio
    };
  }, [portfolioItems]);

  // Prepare asset class data for display
  const assetClassData = useMemo(() => {
    if (!portfolioMetrics) return [];
    
    return Object.entries(portfolioMetrics.assetClassDistribution).map(([name, count]) => ({
      name,
      value: count,
      percentage: ((count / portfolioMetrics.totalFunds) * 100).toFixed(1)
    }));
  }, [portfolioMetrics]);

  const riskProfileData = useMemo(() => {
    if (!portfolioMetrics) return [];
    
    return Object.entries(portfolioMetrics.riskDistribution).map(([profile, value]) => ({
      name: profile.charAt(0).toUpperCase() + profile.slice(1).replace('_', ' '),
      value: value,
      percentage: value > 0 ? ((value / portfolioItems.length) * 100).toFixed(1) : '0'
    })).filter(item => item.value > 0);
  }, [portfolioMetrics, portfolioItems.length]);

  // Chart colors
  const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#84CC16'];

  if (!portfolioMetrics) {
    return (
      <div className={cn("bg-gray-50 rounded-lg p-4 text-center", className)}>
        <p className="text-sm text-gray-500">No portfolio data available</p>
      </div>
    );
  }

  return (
    <div className={cn("bg-white rounded-lg border border-gray-200 p-4", className)}>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center space-x-2 mb-4">
          <Target className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">Portfolio Overview</h3>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 gap-4 text-center">
          <div className="bg-blue-50 p-3 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">{portfolioMetrics.totalFunds}</div>
            <div className="text-xs text-blue-600">Total Funds</div>
          </div>
          
          <div className="bg-green-50 p-3 rounded-lg">
            <div className="text-2xl font-bold text-green-600">{portfolioMetrics.uniqueAssetClasses}</div>
            <div className="text-xs text-green-600">Asset Classes</div>
          </div>
        </div>

        {/* Quality Indicators */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Award className="h-4 w-4 text-gray-500" />
              <span className="text-sm text-gray-600">Data Confidence</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-16 bg-gray-200 rounded-full h-1.5">
                <div 
                  className={cn(
                    "h-1.5 rounded-full",
                    portfolioMetrics.avgConfidence >= 0.8 ? "bg-green-500" :
                    portfolioMetrics.avgConfidence >= 0.6 ? "bg-yellow-500" : "bg-red-500"
                  )}
                  style={{ width: `${portfolioMetrics.avgConfidence * 100}%` }}
                />
              </div>
              <span className="text-sm font-medium">{Math.round(portfolioMetrics.avgConfidence * 100)}%</span>
            </div>
          </div>

          {portfolioMetrics.avgExpenseRatio && (
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <TrendingUp className="h-4 w-4 text-gray-500" />
                <span className="text-sm text-gray-600">Avg. Expense Ratio</span>
              </div>
              <span className="text-sm font-medium">{portfolioMetrics.avgExpenseRatio.toFixed(2)}%</span>
            </div>
          )}

          {portfolioMetrics.needsProspectus > 0 && (
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Shield className="h-4 w-4 text-gray-500" />
                <span className="text-sm text-gray-600">Needs Analysis</span>
              </div>
              <span className="text-sm font-medium">{portfolioMetrics.needsProspectus} funds</span>
            </div>
          )}
        </div>

        {/* Warnings */}
        {portfolioMetrics.lowConfidenceCount > 0 && (
          <div className="flex items-center space-x-2 p-2 bg-yellow-50 rounded-lg">
            <AlertTriangle className="h-4 w-4 text-yellow-600" />
            <span className="text-xs text-yellow-700">
              {portfolioMetrics.lowConfidenceCount} funds have low confidence scores (&lt;70%)
            </span>
          </div>
        )}

        {/* Asset Class Distribution - Simple List */}
        <div>
          <div className="flex items-center space-x-2 mb-2">
            <PieChart className="h-4 w-4 text-gray-500" />
            <h4 className="text-sm font-medium text-gray-900">Asset Class Distribution</h4>
          </div>
          
          <div className="space-y-2">
            {assetClassData.map((entry, index) => (
              <div key={entry.name} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <div className="flex items-center space-x-2">
                  <div 
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <span className="text-sm text-gray-700">{entry.name}</span>
                </div>
                <span className="text-sm font-medium text-gray-900">{entry.value} ({entry.percentage}%)</span>
              </div>
            ))}
          </div>
        </div>

        {/* Risk Profile Distribution - Simple List */}
        {riskProfileData.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-2">Risk Profile Allocation</h4>
            <div className="space-y-1">
              {riskProfileData.map((entry, index) => (
                <div key={entry.name} className="flex items-center justify-between text-xs p-2 bg-gray-50 rounded">
                  <span className="text-gray-700">{entry.name}</span>
                  <span className="font-medium text-gray-900">{entry.value.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Fund List Summary */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">Holdings Summary</h4>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {portfolioItems.slice(0, 10).map((item, index) => (
              <div key={`${item.ticker}-${index}`} className="flex items-center justify-between py-1 text-xs">
                <div className="flex items-center space-x-2">
                  <span className="font-medium text-gray-900">{item.ticker}</span>
                  <span className="text-gray-500 truncate max-w-32">{item.name}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <span className="text-gray-600">{item.asset_class}</span>
                  <div className={cn(
                    "w-2 h-2 rounded-full",
                    item.confidence_score >= 0.8 ? "bg-green-400" :
                    item.confidence_score >= 0.6 ? "bg-yellow-400" : "bg-red-400"
                  )} />
                </div>
              </div>
            ))}
            {portfolioItems.length > 10 && (
              <div className="text-xs text-gray-500 text-center pt-2">
                ... and {portfolioItems.length - 10} more funds
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
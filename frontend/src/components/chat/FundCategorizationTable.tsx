"use client";

import React, { useState, useMemo } from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  Edit3, 
  Filter,
  ChevronDown,
  ChevronRight,
  MoreHorizontal,
  Check,
  X,
  Info,
  TrendingUp,
  TrendingDown,
  Minus
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface FundCategorization {
  ticker: string;
  fundName: string;
  assetClass: 'Equity' | 'Fixed Income' | 'Cash' | 'Alternatives';
  confidence: number;
  subCategories: {
    equityRegion?: 'US' | 'International' | 'Emerging' | 'Global';
    equityStyle?: 'Value' | 'Growth' | 'Blend';
    equitySize?: 'Large' | 'Mid' | 'Small' | 'Micro';
    fixedIncomeType?: 'Government' | 'Corporate' | 'Municipal' | 'High Yield';
    fixedIncomeDuration?: 'Short' | 'Intermediate' | 'Long';
  };
  classificationMethod: string;
  reasoning: string;
  manualOverride: boolean;
  researchSources: string[];
  keyDataPoints: Record<string, any>;
  alternatives: Array<{
    assetClass: string;
    confidence: number;
    reasoning: string;
  }>;
}

interface FundCategorizationTableProps {
  categorizations: FundCategorization[];
  onEdit?: (ticker: string, categorization: Partial<FundCategorization>) => void;
  onApprove?: (ticker: string) => void;
  onBulkApprove?: (tickers: string[]) => void;
  className?: string;
  showFilters?: boolean;
  allowBulkActions?: boolean;
}

type SortField = 'ticker' | 'fundName' | 'assetClass' | 'confidence';
type SortDirection = 'asc' | 'desc';

export function FundCategorizationTable({
  categorizations,
  onEdit,
  onApprove,
  onBulkApprove,
  className,
  showFilters = true,
  allowBulkActions = true
}: FundCategorizationTableProps) {
  const [sortField, setSortField] = useState<SortField>('confidence');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [filterAssetClass, setFilterAssetClass] = useState<string>('all');
  const [filterConfidence, setFilterConfidence] = useState<string>('all');
  const [selectedFunds, setSelectedFunds] = useState<Set<string>>(new Set());
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [editingRow, setEditingRow] = useState<string | null>(null);

  // Confidence color mapping
  const getConfidenceColor = (confidence: number): { bg: string; text: string; border: string } => {
    if (confidence >= 0.9) return { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' };
    if (confidence >= 0.8) return { bg: 'bg-green-50', text: 'text-green-600', border: 'border-green-100' };
    if (confidence >= 0.7) return { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200' };
    if (confidence >= 0.5) return { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' };
    return { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' };
  };

  // Asset class color mapping
  const getAssetClassColor = (assetClass: string): { bg: string; text: string } => {
    const colors = {
      'Equity': { bg: 'bg-blue-50', text: 'text-blue-700' },
      'Fixed Income': { bg: 'bg-purple-50', text: 'text-purple-700' },
      'Cash': { bg: 'bg-green-50', text: 'text-green-700' },
      'Alternatives': { bg: 'bg-orange-50', text: 'text-orange-700' }
    };
    return colors[assetClass as keyof typeof colors] || { bg: 'bg-gray-50', text: 'text-gray-700' };
  };

  // Filter and sort data
  const filteredAndSortedData = useMemo(() => {
    let filtered = categorizations;

    // Apply filters
    if (filterAssetClass !== 'all') {
      filtered = filtered.filter(item => item.assetClass === filterAssetClass);
    }

    if (filterConfidence !== 'all') {
      switch (filterConfidence) {
        case 'high':
          filtered = filtered.filter(item => item.confidence >= 0.8);
          break;
        case 'medium':
          filtered = filtered.filter(item => item.confidence >= 0.6 && item.confidence < 0.8);
          break;
        case 'low':
          filtered = filtered.filter(item => item.confidence < 0.6);
          break;
      }
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aValue = a[sortField];
      let bValue = b[sortField];

      if (typeof aValue === 'string') {
        aValue = aValue.toLowerCase();
        bValue = (bValue as string).toLowerCase();
      }

      let comparison = 0;
      if (aValue < bValue) comparison = -1;
      if (aValue > bValue) comparison = 1;

      return sortDirection === 'desc' ? -comparison : comparison;
    });

    return filtered;
  }, [categorizations, filterAssetClass, filterConfidence, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const handleSelectFund = (ticker: string, selected: boolean) => {
    const newSelected = new Set(selectedFunds);
    if (selected) {
      newSelected.add(ticker);
    } else {
      newSelected.delete(ticker);
    }
    setSelectedFunds(newSelected);
  };

  const handleSelectAll = (selected: boolean) => {
    if (selected) {
      setSelectedFunds(new Set(filteredAndSortedData.map(item => item.ticker)));
    } else {
      setSelectedFunds(new Set());
    }
  };

  const toggleRowExpanded = (ticker: string) => {
    const newExpanded = new Set(expandedRows);
    if (expandedRows.has(ticker)) {
      newExpanded.delete(ticker);
    } else {
      newExpanded.add(ticker);
    }
    setExpandedRows(newExpanded);
  };

  const renderSubCategories = (categorization: FundCategorization) => {
    const { subCategories } = categorization;
    const items = [];

    if (categorization.assetClass === 'Equity') {
      if (subCategories.equityRegion) {
        items.push({ label: 'Region', value: subCategories.equityRegion });
      }
      if (subCategories.equityStyle) {
        items.push({ label: 'Style', value: subCategories.equityStyle });
      }
      if (subCategories.equitySize) {
        items.push({ label: 'Size', value: subCategories.equitySize });
      }
    } else if (categorization.assetClass === 'Fixed Income') {
      if (subCategories.fixedIncomeType) {
        items.push({ label: 'Type', value: subCategories.fixedIncomeType });
      }
      if (subCategories.fixedIncomeDuration) {
        items.push({ label: 'Duration', value: subCategories.fixedIncomeDuration });
      }
    }

    if (items.length === 0) return <span className="text-gray-400 text-sm">None specified</span>;

    return (
      <div className="flex flex-wrap gap-1">
        {items.map((item, index) => (
          <span
            key={index}
            className="inline-flex items-center px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded-md"
          >
            {item.label}: {item.value}
          </span>
        ))}
      </div>
    );
  };

  const renderConfidenceBadge = (confidence: number, manualOverride: boolean) => {
    const colors = getConfidenceColor(confidence);
    
    return (
      <div className="flex items-center gap-2">
        <div className={cn(
          "flex items-center justify-center w-16 h-8 rounded-full text-sm font-medium",
          colors.bg, colors.text, colors.border, "border"
        )}>
          {Math.round(confidence * 100)}%
        </div>
        {manualOverride && (
          <div className="flex items-center gap-1 text-xs text-blue-600">
            <Edit3 className="w-3 h-3" />
            Manual
          </div>
        )}
      </div>
    );
  };

  const renderExpandedRow = (categorization: FundCategorization) => (
    <tr className="bg-gray-50">
      <td colSpan={7} className="px-6 py-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
          {/* Classification Details */}
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Classification Details</h4>
            <div className="space-y-1 text-gray-600">
              <div><span className="font-medium">Method:</span> {categorization.classificationMethod}</div>
              <div><span className="font-medium">Reasoning:</span> {categorization.reasoning}</div>
            </div>
          </div>

          {/* Research Sources */}
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Research Sources</h4>
            <div className="space-y-1">
              {categorization.researchSources.length > 0 ? (
                categorization.researchSources.map((source, index) => (
                  <div key={index} className="text-gray-600 text-xs">{source}</div>
                ))
              ) : (
                <div className="text-gray-400 text-xs">No sources available</div>
              )}
            </div>
          </div>

          {/* Alternative Classifications */}
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Alternatives</h4>
            <div className="space-y-1">
              {categorization.alternatives.length > 0 ? (
                categorization.alternatives.slice(0, 3).map((alt, index) => (
                  <div key={index} className="flex items-center justify-between text-xs">
                    <span className="text-gray-600">{alt.assetClass}</span>
                    <span className="text-gray-500">{Math.round(alt.confidence * 100)}%</span>
                  </div>
                ))
              ) : (
                <div className="text-gray-400 text-xs">No alternatives</div>
              )}
            </div>
          </div>
        </div>
      </td>
    </tr>
  );

  return (
    <div className={cn("w-full", className)}>
      {/* Filters and Controls */}
      {showFilters && (
        <div className="mb-6 space-y-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">Filters:</span>
            </div>

            <select
              value={filterAssetClass}
              onChange={(e) => setFilterAssetClass(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Asset Classes</option>
              <option value="Equity">Equity</option>
              <option value="Fixed Income">Fixed Income</option>
              <option value="Cash">Cash</option>
              <option value="Alternatives">Alternatives</option>
            </select>

            <select
              value={filterConfidence}
              onChange={(e) => setFilterConfidence(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Confidence Levels</option>
              <option value="high">High (≥80%)</option>
              <option value="medium">Medium (60-79%)</option>
              <option value="low">Low (&lt;60%)</option>
            </select>

            {allowBulkActions && selectedFunds.size > 0 && (
              <div className="flex items-center gap-2 ml-auto">
                <span className="text-sm text-gray-600">
                  {selectedFunds.size} selected
                </span>
                <button
                  onClick={() => onBulkApprove?.(Array.from(selectedFunds))}
                  className="px-3 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors"
                >
                  Approve Selected
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 rounded-lg">
        <table className="min-w-full divide-y divide-gray-300">
          <thead className="bg-gray-50">
            <tr>
              {allowBulkActions && (
                <th className="px-6 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={filteredAndSortedData.length > 0 && selectedFunds.size === filteredAndSortedData.length}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                </th>
              )}
              
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('ticker')}
                  className="flex items-center gap-1 hover:text-gray-700"
                >
                  Fund
                  {sortField === 'ticker' && (
                    sortDirection === 'desc' ? <TrendingDown className="w-3 h-3" /> : <TrendingUp className="w-3 h-3" />
                  )}
                </button>
              </th>

              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('assetClass')}
                  className="flex items-center gap-1 hover:text-gray-700"
                >
                  Asset Class
                  {sortField === 'assetClass' && (
                    sortDirection === 'desc' ? <TrendingDown className="w-3 h-3" /> : <TrendingUp className="w-3 h-3" />
                  )}
                </button>
              </th>

              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Sub-Categories
              </th>

              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('confidence')}
                  className="flex items-center gap-1 hover:text-gray-700"
                >
                  Confidence
                  {sortField === 'confidence' && (
                    sortDirection === 'desc' ? <TrendingDown className="w-3 h-3" /> : <TrendingUp className="w-3 h-3" />
                  )}
                </button>
              </th>

              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>

              <th className="relative px-6 py-3">
                <span className="sr-only">Expand</span>
              </th>
            </tr>
          </thead>

          <tbody className="bg-white divide-y divide-gray-200">
            {filteredAndSortedData.map((categorization) => {
              const isExpanded = expandedRows.has(categorization.ticker);
              const isSelected = selectedFunds.has(categorization.ticker);
              const assetClassColors = getAssetClassColor(categorization.assetClass);
              
              return (
                <React.Fragment key={categorization.ticker}>
                  <tr className={cn(
                    "hover:bg-gray-50 transition-colors",
                    isSelected && "bg-blue-50"
                  )}>
                    {allowBulkActions && (
                      <td className="px-6 py-4">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => handleSelectFund(categorization.ticker, e.target.checked)}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                      </td>
                    )}

                    <td className="px-6 py-4">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {categorization.ticker}
                        </div>
                        <div className="text-sm text-gray-500 max-w-xs truncate">
                          {categorization.fundName}
                        </div>
                      </div>
                    </td>

                    <td className="px-6 py-4">
                      <span className={cn(
                        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                        assetClassColors.bg, assetClassColors.text
                      )}>
                        {categorization.assetClass}
                      </span>
                    </td>

                    <td className="px-6 py-4">
                      {renderSubCategories(categorization)}
                    </td>

                    <td className="px-6 py-4">
                      {renderConfidenceBadge(categorization.confidence, categorization.manualOverride)}
                    </td>

                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {categorization.confidence < 0.8 && (
                          <button
                            onClick={() => onEdit?.(categorization.ticker, categorization)}
                            className="text-blue-600 hover:text-blue-900 transition-colors"
                          >
                            <Edit3 className="w-4 h-4" />
                          </button>
                        )}
                        
                        <button
                          onClick={() => onApprove?.(categorization.ticker)}
                          className="text-green-600 hover:text-green-900 transition-colors"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                      </div>
                    </td>

                    <td className="px-6 py-4">
                      <button
                        onClick={() => toggleRowExpanded(categorization.ticker)}
                        className="text-gray-400 hover:text-gray-600 transition-colors"
                      >
                        {isExpanded ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                      </button>
                    </td>
                  </tr>

                  {isExpanded && renderExpandedRow(categorization)}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>

        {filteredAndSortedData.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-500 text-sm">
              No funds match the current filters
            </div>
          </div>
        )}
      </div>

      {/* Summary */}
      <div className="mt-4 flex items-center justify-between text-sm text-gray-500">
        <div>
          Showing {filteredAndSortedData.length} of {categorizations.length} funds
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-green-100 rounded-full"></div>
            <span>High confidence</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-yellow-100 rounded-full"></div>
            <span>Medium confidence</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-red-100 rounded-full"></div>
            <span>Low confidence</span>
          </div>
        </div>
      </div>
    </div>
  );
}
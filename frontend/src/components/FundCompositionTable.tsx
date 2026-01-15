"use client";

import { useMemo, useState } from "react";
import { FundData } from "@/lib/types";
import { ChevronDown, ChevronUp, Download, Search, TrendingUp, TrendingDown, Minus } from "lucide-react";

interface FundCompositionTableProps {
  funds: FundData[];
}

type SortField = 'fund_name' | 'expense_ratio' | 'one_year_return' | 'net_assets_usd' | 'equity_pct';
type SortDirection = 'asc' | 'desc';

export function FundCompositionTable({ funds }: FundCompositionTableProps) {
  const [sortField, setSortField] = useState<SortField>('fund_name');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const toggleRowExpansion = (fundName: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(fundName)) {
      newExpanded.delete(fundName);
    } else {
      newExpanded.add(fundName);
    }
    setExpandedRows(newExpanded);
  };

  const filteredAndSortedFunds = useMemo(() => {
    let filtered = funds.filter(fund =>
      fund.fund_name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return filtered.sort((a, b) => {
      let aValue = a[sortField];
      let bValue = b[sortField];

      // Handle null/undefined values
      if (aValue === null || aValue === undefined) aValue = sortField === 'fund_name' ? '' : 0;
      if (bValue === null || bValue === undefined) bValue = sortField === 'fund_name' ? '' : 0;

      if (sortField === 'fund_name') {
        aValue = (aValue as string).toLowerCase();
        bValue = (bValue as string).toLowerCase();
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [funds, sortField, sortDirection, searchTerm]);

  const exportToCSV = () => {
    const headers = [
      'Fund Name',
      'Expense Ratio (%)',
      '1-Year Return (%)',
      'Net Assets ($)',
      'NAV',
      'Equity %',
      'Fixed Income %',
      'Money Market %',
      'Other %',
      'Management Fee (%)',
      'Portfolio Turnover (%)'
    ];

    const csvData = filteredAndSortedFunds.map(fund => [
      fund.fund_name,
      fund.expense_ratio ?? 'N/A',
      fund.one_year_return ?? 'N/A',
      fund.net_assets_usd ?? 'N/A',
      fund.nav ?? 'N/A',
      fund.equity_pct ?? 'N/A',
      fund.fixed_income_pct ?? 'N/A',
      fund.money_market_pct ?? 'N/A',
      fund.other_pct ?? 'N/A',
      fund.management_fee ?? 'N/A',
      fund.portfolio_turnover ?? 'N/A'
    ]);

    const csvContent = [headers, ...csvData]
      .map(row => row.map(field => `"${field}"`).join(','))
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'fund_composition.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatCurrency = (value: number | undefined | null) => {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatPercentage = (value: number | undefined | null, decimals = 2) => {
    if (value === null || value === undefined) return 'N/A';
    return `${value.toFixed(decimals)}%`;
  };

  const formatNumber = (value: number | undefined | null, decimals = 2) => {
    if (value === null || value === undefined) return 'N/A';
    return value.toFixed(decimals);
  };

  const getReturnIcon = (returnValue: number | undefined | null) => {
    if (returnValue === null || returnValue === undefined) return <Minus className="h-4 w-4 text-gray-400" />;
    if (returnValue > 0) return <TrendingUp className="h-4 w-4 text-green-400" />;
    if (returnValue < 0) return <TrendingDown className="h-4 w-4 text-red-400" />;
    return <Minus className="h-4 w-4 text-gray-400" />;
  };

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return null;
    return sortDirection === 'asc' ? 
      <ChevronUp className="h-4 w-4" /> : 
      <ChevronDown className="h-4 w-4" />;
  };

  if (funds.length === 0) {
    return (
      <div className="space-y-6">
        <div className="text-center py-12">
          <div className="text-gray-400 text-lg">No fund data to display</div>
          <div className="text-gray-500 text-sm">Fund composition will appear after processing</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white mb-2">📊 Fund Composition Analysis</h2>
          <p className="text-gray-400 text-sm">
            {filteredAndSortedFunds.length} fund{filteredAndSortedFunds.length !== 1 ? 's' : ''} extracted from your documents
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search funds..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>
          
          {/* Export Button */}
          <button
            onClick={exportToCSV}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            <Download className="h-4 w-4" />
            <span className="text-sm font-medium">Export CSV</span>
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700 bg-gray-800/30">
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('fund_name')}
                    className="flex items-center space-x-1 hover:text-white transition-colors"
                  >
                    <span>Fund Name</span>
                    {getSortIcon('fund_name')}
                  </button>
                </th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('expense_ratio')}
                    className="flex items-center space-x-1 hover:text-white transition-colors"
                  >
                    <span>Expense Ratio</span>
                    {getSortIcon('expense_ratio')}
                  </button>
                </th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('one_year_return')}
                    className="flex items-center space-x-1 hover:text-white transition-colors"
                  >
                    <span>1-Year Return</span>
                    {getSortIcon('one_year_return')}
                  </button>
                </th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Asset Allocation</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('net_assets_usd')}
                    className="flex items-center space-x-1 hover:text-white transition-colors"
                  >
                    <span>Net Assets</span>
                    {getSortIcon('net_assets_usd')}
                  </button>
                </th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filteredAndSortedFunds.map((fund, index) => (
                <>
                  {/* Main Row */}
                  <tr key={fund.fund_name} className={`hover:bg-gray-800/30 transition-colors ${index % 2 === 0 ? 'bg-gray-900/20' : ''}`}>
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-white">{fund.fund_name}</div>
                      {fund.report_date && (
                        <div className="text-xs text-gray-400">Report: {fund.report_date}</div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-white">{formatPercentage(fund.expense_ratio)}</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        {getReturnIcon(fund.one_year_return)}
                        <span className={`text-sm font-medium ${
                          fund.one_year_return && fund.one_year_return > 0 ? 'text-green-400' :
                          fund.one_year_return && fund.one_year_return < 0 ? 'text-red-400' :
                          'text-gray-400'
                        }`}>
                          {formatPercentage(fund.one_year_return)}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-gray-400">Equity:</span>
                          <span className="text-blue-300">{formatPercentage(fund.equity_pct)}</span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-gray-400">Fixed Inc:</span>
                          <span className="text-green-300">{formatPercentage(fund.fixed_income_pct)}</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-white">{formatCurrency(fund.net_assets_usd)}</span>
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => toggleRowExpansion(fund.fund_name)}
                        className="flex items-center space-x-1 text-blue-400 hover:text-blue-300 transition-colors text-sm"
                      >
                        <span>{expandedRows.has(fund.fund_name) ? 'Less' : 'More'}</span>
                        {expandedRows.has(fund.fund_name) ? 
                          <ChevronUp className="h-4 w-4" /> : 
                          <ChevronDown className="h-4 w-4" />
                        }
                      </button>
                    </td>
                  </tr>

                  {/* Expanded Row */}
                  {expandedRows.has(fund.fund_name) && (
                    <tr className="bg-gray-800/20">
                      <td colSpan={6} className="px-6 py-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                          {/* Asset Allocation Details */}
                          <div className="space-y-2">
                            <h4 className="text-sm font-medium text-blue-400">Asset Allocation</h4>
                            <div className="space-y-1 text-xs">
                              <div className="flex justify-between">
                                <span className="text-gray-400">Money Market:</span>
                                <span className="text-yellow-300">{formatPercentage(fund.money_market_pct)}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-400">Other:</span>
                                <span className="text-purple-300">{formatPercentage(fund.other_pct)}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-400">Target Equity:</span>
                                <span className="text-gray-300">{formatPercentage(fund.target_equity_pct)}</span>
                              </div>
                            </div>
                          </div>

                          {/* Financial Metrics */}
                          <div className="space-y-2">
                            <h4 className="text-sm font-medium text-green-400">Financial Metrics</h4>
                            <div className="space-y-1 text-xs">
                              <div className="flex justify-between">
                                <span className="text-gray-400">NAV:</span>
                                <span className="text-white">${formatNumber(fund.nav)}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-400">Management Fee:</span>
                                <span className="text-white">{formatPercentage(fund.management_fee)}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-400">Portfolio Turnover:</span>
                                <span className="text-white">{formatPercentage(fund.portfolio_turnover)}</span>
                              </div>
                            </div>
                          </div>

                          {/* Risk & Flow Metrics */}
                          <div className="space-y-2">
                            <h4 className="text-sm font-medium text-red-400">Risk & Flows</h4>
                            <div className="space-y-1 text-xs">
                              <div className="flex justify-between">
                                <span className="text-gray-400">Net Investment Income:</span>
                                <span className="text-white">{formatCurrency(fund.net_investment_income)}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-400">Total Distributions:</span>
                                <span className="text-white">{formatCurrency(fund.total_distributions)}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-400">Net Asset Change:</span>
                                <span className={`${
                                  fund.net_asset_change && fund.net_asset_change > 0 ? 'text-green-300' :
                                  fund.net_asset_change && fund.net_asset_change < 0 ? 'text-red-300' :
                                  'text-white'
                                }`}>
                                  {formatCurrency(fund.net_asset_change)}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <div className="text-sm text-gray-400">Total Funds</div>
          <div className="text-2xl font-bold text-white">{filteredAndSortedFunds.length}</div>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <div className="text-sm text-gray-400">Avg Expense Ratio</div>
          <div className="text-2xl font-bold text-blue-400">
            {formatPercentage(
              filteredAndSortedFunds
                .filter(f => f.expense_ratio !== null && f.expense_ratio !== undefined)
                .reduce((sum, f) => sum + (f.expense_ratio || 0), 0) /
              filteredAndSortedFunds.filter(f => f.expense_ratio !== null && f.expense_ratio !== undefined).length
            )}
          </div>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <div className="text-sm text-gray-400">Avg 1Y Return</div>
          <div className="text-2xl font-bold text-green-400">
            {formatPercentage(
              filteredAndSortedFunds
                .filter(f => f.one_year_return !== null && f.one_year_return !== undefined)
                .reduce((sum, f) => sum + (f.one_year_return || 0), 0) /
              filteredAndSortedFunds.filter(f => f.one_year_return !== null && f.one_year_return !== undefined).length
            )}
          </div>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <div className="text-sm text-gray-400">Total Net Assets</div>
          <div className="text-2xl font-bold text-purple-400">
            {formatCurrency(
              filteredAndSortedFunds
                .filter(f => f.net_assets_usd !== null && f.net_assets_usd !== undefined)
                .reduce((sum, f) => sum + (f.net_assets_usd || 0), 0)
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
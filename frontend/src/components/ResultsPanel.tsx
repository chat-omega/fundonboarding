"use client";

import { useState } from "react";
import { Search, Download, FileText, TrendingUp, DollarSign, Target, AlertTriangle } from "lucide-react";
import { FundData } from "@/lib/types";
import { formatCurrency, formatPercentage } from "@/lib/utils";

interface ResultsPanelProps {
  funds: FundData[];
  selectedFund: FundData | null;
  onSelectFund: (fund: FundData | null) => void;
  extractionStatus: string;
}

export function ResultsPanel({
  funds,
  selectedFund,
  onSelectFund,
  extractionStatus
}: ResultsPanelProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState<keyof FundData>("fund_name");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  const filteredFunds = funds.filter(fund =>
    fund.fund_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const sortedFunds = [...filteredFunds].sort((a, b) => {
    const aVal = a[sortBy];
    const bVal = b[sortBy];
    
    if (aVal === undefined) return 1;
    if (bVal === undefined) return -1;
    
    const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    return sortOrder === "asc" ? comparison : -comparison;
  });


  const exportToCsv = () => {
    if (funds.length === 0) return;
    
    const headers = Object.keys(funds[0]).join(",");
    const rows = funds.map(fund => 
      Object.values(fund).map(val => `"${val || ""}"`).join(",")
    ).join("\n");
    
    const csv = `${headers}\n${rows}`;
    const blob = new Blob([csv], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `fund_extraction_${new Date().toISOString().split("T")[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  const exportToJson = () => {
    if (funds.length === 0) return;
    
    const json = JSON.stringify(funds, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `fund_extraction_${new Date().toISOString().split("T")[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  if (extractionStatus === "idle") {
    return (
      <div className="h-full flex flex-col">
        <h2 className="text-xl font-bold text-white mb-4">📊 Extraction Results</h2>
        
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-4">
            <FileText className="h-16 w-16 text-gray-600 mx-auto" />
            <div>
              <p className="text-gray-400 text-lg">No data yet</p>
              <p className="text-gray-500 text-sm">Upload and extract a PDF to see results</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">📊 Extraction Results</h2>
        
        {funds.length > 0 && (
          <div className="flex space-x-2">
            <button
              onClick={exportToCsv}
              className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded-md flex items-center space-x-1 transition-colors"
            >
              <Download className="h-3 w-3" />
              <span>CSV</span>
            </button>
            <button
              onClick={exportToJson}
              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-md flex items-center space-x-1 transition-colors"
            >
              <Download className="h-3 w-3" />
              <span>JSON</span>
            </button>
          </div>
        )}
      </div>

      {funds.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-4">
            <div className="animate-pulse">
              <FileText className="h-16 w-16 text-gray-600 mx-auto" />
            </div>
            <div>
              <p className="text-gray-400 text-lg">
                {extractionStatus === "processing" ? "Extracting..." : "Waiting for results"}
              </p>
              <p className="text-gray-500 text-sm">Fund data will appear here</p>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* Search and Controls */}
          <div className="space-y-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search funds..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div className="flex space-x-2">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as keyof FundData)}
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="fund_name">Fund Name</option>
                <option value="nav">NAV</option>
                <option value="one_year_return">1Y Return</option>
                <option value="expense_ratio">Expense Ratio</option>
                <option value="net_assets_usd">Net Assets</option>
              </select>
              
              <button
                onClick={() => setSortOrder(sortOrder === "asc" ? "desc" : "asc")}
                className="px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors"
              >
                {sortOrder === "asc" ? "↑" : "↓"}
              </button>
            </div>
          </div>

          {/* Results Summary */}
          <div className="bg-gray-800/30 rounded-lg p-3 border border-gray-700">
            <div className="text-sm text-gray-400 mb-2">Summary</div>
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-white font-medium">{sortedFunds.length}</span>
                <span className="text-gray-400"> funds found</span>
              </div>
              <div>
                <span className="text-green-400 font-medium">
                  {funds.filter(f => f.one_year_return && f.one_year_return > 0).length}
                </span>
                <span className="text-gray-400"> positive returns</span>
              </div>
            </div>
          </div>

          {/* Fund List */}
          <div className="flex-1 overflow-hidden flex flex-col">
            <div className="flex-1 overflow-y-auto space-y-2">
              {sortedFunds.map((fund, idx) => (
                <div
                  key={idx}
                  onClick={() => onSelectFund(selectedFund === fund ? null : fund)}
                  className={`
                    cursor-pointer p-3 rounded-lg border transition-all duration-200
                    ${selectedFund === fund
                      ? "bg-blue-500/20 border-blue-500"
                      : "bg-gray-800/50 border-gray-700 hover:bg-gray-800/70"
                    }
                  `}
                >
                  <div className="space-y-2">
                    <div>
                      <h4 className="text-white font-medium text-sm leading-tight">
                        {fund.fund_name || "Unnamed Fund"}
                      </h4>
                      <p className="text-gray-400 text-xs">
                        {fund.report_date || "No date"}
                      </p>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-1">
                          <DollarSign className="h-3 w-3 text-green-400" />
                          <span className="text-gray-400">NAV:</span>
                          <span className="text-white">{formatCurrency(fund.nav)}</span>
                        </div>
                        
                        <div className="flex items-center space-x-1">
                          <TrendingUp className="h-3 w-3 text-blue-400" />
                          <span className="text-gray-400">1Y Return:</span>
                          <span className={`${fund.one_year_return && fund.one_year_return >= 0 ? "text-green-400" : "text-red-400"}`}>
                            {formatPercentage(fund.one_year_return)}
                          </span>
                        </div>
                      </div>
                      
                      <div className="space-y-1">
                        <div className="flex items-center space-x-1">
                          <Target className="h-3 w-3 text-purple-400" />
                          <span className="text-gray-400">Expense:</span>
                          <span className="text-white">{formatPercentage(fund.expense_ratio)}</span>
                        </div>
                        
                        <div className="flex items-center space-x-1">
                          <AlertTriangle className="h-3 w-3 text-orange-400" />
                          <span className="text-gray-400">Assets:</span>
                          <span className="text-white">{formatCurrency(fund.net_assets_usd)}</span>
                        </div>
                      </div>
                    </div>
                    
                    {/* Asset Allocation Preview */}
                    {(fund.equity_pct || fund.fixed_income_pct) && (
                      <div className="pt-2 border-t border-gray-700">
                        <div className="text-xs text-gray-400 mb-1">Asset Allocation</div>
                        <div className="flex space-x-4 text-xs">
                          {fund.equity_pct && (
                            <span className="text-blue-400">
                              Equity: {fund.equity_pct.toFixed(1)}%
                            </span>
                          )}
                          {fund.fixed_income_pct && (
                            <span className="text-green-400">
                              Fixed: {fund.fixed_income_pct.toFixed(1)}%
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Selected Fund Details */}
          {selectedFund && (
            <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700 max-h-60 overflow-y-auto">
              <h4 className="text-white font-medium mb-3">{selectedFund.fund_name}</h4>
              
              <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
                {Object.entries(selectedFund).map(([key, value]) => {
                  if (!value || key === "fund_name") return null;
                  
                  return (
                    <div key={key} className="flex justify-between">
                      <span className="text-gray-400 capitalize">
                        {key.replace(/_/g, " ")}:
                      </span>
                      <span className="text-white">
                        {typeof value === "number" 
                          ? key.includes("pct") || key.includes("return") || key.includes("ratio")
                            ? formatPercentage(value)
                            : key.includes("usd") || key.includes("assets") || key.includes("nav")
                              ? formatCurrency(value)
                              : value.toFixed(2)
                          : value
                        }
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
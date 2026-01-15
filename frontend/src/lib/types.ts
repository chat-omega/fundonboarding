// Type definitions for the Fund Extraction application

export interface FundData {
  fund_name: string;
  target_equity_pct?: number;
  report_date?: string;
  
  // Asset Allocation
  equity_pct?: number;
  fixed_income_pct?: number;
  money_market_pct?: number;
  other_pct?: number;
  
  // Metrics
  nav?: number;
  net_assets_usd?: number;
  expense_ratio?: number;
  management_fee?: number;
  
  // Performance
  one_year_return?: number;
  portfolio_turnover?: number;
  
  // Risk Metrics
  equity_futures_notional?: number;
  bond_futures_notional?: number;
  
  // Fund Flows
  net_investment_income?: number;
  total_distributions?: number;
  net_asset_change?: number;
  
  // Calculated fields
  return_per_risk?: number;
  drift?: number;
}

export interface ExtractEvent {
  type: "text" | "status" | "results" | "error" | "fund_discovered" | "fund_extracted";
  data: {
    content?: string;
    stage?: string;
    progress?: number;
    message?: string;
    funds?: FundData[];
    fund?: FundData;
    fund_name?: string;
    page_count?: number;
    summary?: {
      total_funds: number;
      pages_processed: number;
      fund_sections: string[];
      session_id: string;
    };
    analysis?: {
      return_per_risk?: Record<string, number>;
      allocation_drift?: Record<string, number>;
      performance_stats?: {
        mean_return: number;
        max_return: number;
        min_return: number;
        std_return: number;
      };
      expense_stats?: {
        mean_expense: number;
        max_expense: number;
        min_expense: number;
      };
      allocation_summary?: Record<string, {
        mean: number;
        range: [number, number];
      }>;
    };
  };
}

export interface UploadResponse {
  file_path: string;
  filename: string;
  size: number;
}

export type ExtractionStatus = 
  | "idle" 
  | "uploading" 
  | "uploaded" 
  | "processing" 
  | "completed" 
  | "error";

export interface StageStatus {
  name: string;
  status: "pending" | "processing" | "completed" | "error";
}

export interface ChartData {
  name: string;
  value: number;
  target?: number;
}

export interface PerformanceData {
  fund_name: string;
  return: number;
  risk: number;
  expense_ratio: number;
}
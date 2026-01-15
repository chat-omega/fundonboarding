// Chat-specific type definitions for the Intelligent Fund Onboarding System

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  type?: 'text' | 'file_upload' | 'status' | 'error' | 'fund_data' | 'portfolio_summary';
  metadata?: {
    file_name?: string;
    file_size?: number;
    file_type?: string;
    progress?: number;
    fund_count?: number;
    session_id?: string;
    [key: string]: string | number | boolean | undefined;
  };
}

export interface ChatSession {
  session_id: string;
  created_at: string;
  updated_at: string;
  stage: OnboardingStage;
  progress: number;
  status: SessionStatus;
  chat_history: ChatMessage[];
  portfolio_items_count: number;
  fund_extractions_count: number;
  file_path?: string;
  file_type?: 'csv' | 'excel' | 'pdf' | 'json';
}

export type OnboardingStage = 
  | 'greeting' 
  | 'file_upload' 
  | 'processing' 
  | 'research'
  | 'extraction' 
  | 'analysis' 
  | 'recommendations'
  | 'categorization'
  | 'categorization_review'
  | 'complete';

export type SessionStatus = 
  | 'idle' 
  | 'processing' 
  | 'completed' 
  | 'error';

export interface AgentMessage {
  type: 'connected' | 'status' | 'portfolio_processed' | 'fund_extracted' | 'analysis_complete' | 'error' | 'chat_response' | 'categorization_question' | 'categorization_complete';
  data: {
    message?: string;
    stage?: string;
    progress?: number;
    ticker?: string;
    fund_name?: string;
    confidence?: number;
    total_processed?: number;
    successful_extractions?: number;
    portfolio_items?: PortfolioItem[];
    fund_data?: FundExtraction;
    error?: string;
    session_id?: string;
    question?: CategoryQuestion;
    categorizations?: FundCategorization[];
    [key: string]: any;
  };
  timestamp?: string;
}

export interface PortfolioItem {
  ticker: string;
  name: string;
  asset_class: string;
  expense_ratio?: number;
  morningstar_category?: string;
  conservative_pct?: number;
  mod_conservative_pct?: number;
  moderate_pct?: number;
  growth_pct?: number;
  aggressive_pct?: number;
  confidence_score: number;
  requires_prospectus: boolean;
  prospectus_url?: string;
  prospectus_local_path?: string;
}

export interface FundExtraction {
  ticker: string;
  fund_name?: string;
  nav?: number;
  expense_ratio?: number;
  one_year_return?: number;
  confidence_score: number;
  extraction_method: string;
  processing_time?: number;
  data_source: 'pdf' | 'web' | 'api' | 'manual';
  extracted_at: string;
  [key: string]: any;
}

export interface ProcessingUpdate {
  session_id: string;
  stage: OnboardingStage;
  progress: number;
  status: SessionStatus;
  message: string;
  details?: {
    current_item?: string;
    items_processed?: number;
    total_items?: number;
    errors?: string[];
  };
}

export interface QuickAction {
  id: string;
  label: string;
  action: 'upload_csv' | 'upload_pdf' | 'analyze_portfolio' | 'start_categorization' | 'get_recommendations' | 'export_results';
  icon?: string;
  enabled: boolean;
}

export interface FileUploadProgress {
  file_name: string;
  progress: number;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  error?: string;
}

export interface SessionCreateResponse {
  session_id: string;
  status: string;
  message: string;
}

export interface FileUploadResponse {
  session_id: string;
  file_path: string;
  filename: string;
  size: number;
  file_type: string;
}

export interface PortfolioAnalysis {
  total_funds: number;
  total_allocation: number;
  average_expense_ratio?: number;
  risk_profile_allocations: Record<string, number>;
  asset_class_breakdown: Record<string, number>;
  overall_confidence: number;
  data_completeness: number;
  recommendations: string[];
  warnings: string[];
}

export interface FundCategorization {
  id: string;
  ticker: string;
  fund_name: string;
  asset_class: 'Equity' | 'Fixed Income' | 'Cash' | 'Alternatives';
  equity_region?: 'US' | 'International' | 'Emerging' | 'Global';
  equity_style?: 'Value' | 'Growth' | 'Blend';
  equity_size?: 'Large' | 'Mid' | 'Small' | 'Micro';
  fixed_income_type?: 'Government' | 'Corporate' | 'Municipal' | 'High Yield';
  fixed_income_duration?: 'Short' | 'Intermediate' | 'Long';
  alternatives_type?: string;
  confidence_score: number;
  confidence_factors: ConfidenceFactors;
  research_sources: ResearchSource[];
  alternatives: AlternativeClassification[];
  override_history: OverrideRecord[];
  classification_reasoning: string;
  created_at: string;
  updated_at: string;
  reviewed_by?: string;
  approved: boolean;
}

export interface ConfidenceFactors {
  source_reliability: number;
  data_completeness: number;
  pattern_strength: number;
  cross_validation: number;
  temporal_consistency: number;
  peer_comparison: number;
  expert_validation: number;
  market_data_alignment: number;
  regulatory_compliance: number;
  methodology_robustness: number;
  consensus_agreement: number;
}

export interface ResearchSource {
  type: 'web_search' | 'financial_api' | 'prospectus' | 'fact_sheet' | 'morningstar' | 'bloomberg' | 'yahoo_finance';
  url?: string;
  title: string;
  content_snippet: string;
  reliability_score: number;
  relevance_score: number;
  accessed_at: string;
  cached: boolean;
}

export interface AlternativeClassification {
  asset_class: string;
  equity_region?: string;
  equity_style?: string;
  equity_size?: string;
  fixed_income_type?: string;
  fixed_income_duration?: string;
  alternatives_type?: string;
  confidence: number;
  reasoning: string;
}

export interface OverrideRecord {
  id: string;
  original_classification: Partial<FundCategorization>;
  new_classification: Partial<FundCategorization>;
  reason: string;
  override_by: string;
  override_at: string;
  approved_by?: string;
  approved_at?: string;
}

export interface CategoryQuestion {
  id: string;
  session_id: string;
  question_type: 'asset_class' | 'equity_subcategory' | 'fixed_income_subcategory' | 'alternatives_type';
  question_text: string;
  context: {
    fund_ticker?: string;
    fund_name?: string;
    current_classification?: Partial<FundCategorization>;
    research_summary?: string;
  };
  options: CategoryOption[];
  allow_custom: boolean;
  required: boolean;
  created_at: string;
}

export interface CategoryOption {
  value: string;
  label: string;
  description?: string;
  confidence?: number;
  recommended?: boolean;
}

export interface CategoryResponse {
  question_id: string;
  selected_value: string;
  custom_value?: string;
  confidence_override?: number;
  notes?: string;
  responded_at: string;
}
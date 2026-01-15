"""Unified data models for portfolio and fund data."""

from typing import Dict, List, Optional, Union, Literal, Any
from pydantic import BaseModel, Field
from datetime import datetime

# Import our existing fund data model
import sys
sys.path.append('..')
from src.models import FundData as OriginalFundData


class PortfolioItem(BaseModel):
    """Individual item in a portfolio (from CSV)."""
    
    # Basic identifiers
    ticker: str = Field(..., description="Fund ticker symbol, e.g. 'VTI'")
    name: str = Field(..., description="Fund name, e.g. 'Vanguard Total Stock Market ETF'")
    asset_class: str = Field(..., description="Asset class, e.g. 'U.S. Equity'")
    
    # Portfolio allocation data
    expense_ratio: Optional[float] = Field(None, description="Expense ratio as percentage")
    morningstar_category: Optional[str] = Field(None, description="Morningstar category")
    
    # Risk profile allocations
    conservative_pct: Optional[float] = Field(None, description="Conservative allocation %")
    mod_conservative_pct: Optional[float] = Field(None, description="Moderate Conservative allocation %")
    moderate_pct: Optional[float] = Field(None, description="Moderate allocation %")
    growth_pct: Optional[float] = Field(None, description="Growth allocation %")
    aggressive_pct: Optional[float] = Field(None, description="Aggressive allocation %")
    
    # Processing metadata
    confidence_score: float = Field(0.0, description="Processing confidence score (0.0-1.0)")
    requires_prospectus: bool = Field(True, description="Whether to fetch prospectus")
    prospectus_url: Optional[str] = Field(None, description="URL to fund prospectus")
    prospectus_local_path: Optional[str] = Field(None, description="Local path to prospectus PDF")


class ExtendedFundData(OriginalFundData):
    """Extended fund data that includes our extraction plus additional metadata."""
    
    # Source information
    ticker: Optional[str] = Field(None, description="Fund ticker symbol")
    data_source: Literal["pdf", "web", "api", "manual"] = Field("pdf", description="Data source")
    extraction_method: str = Field("llamaparse", description="Extraction method used")
    source_document: Optional[str] = Field(None, description="Path to source document")
    
    # Quality metrics
    confidence_score: float = Field(0.0, description="Overall extraction confidence (0.0-1.0)")
    completeness_score: float = Field(0.0, description="Data completeness score (0.0-1.0)")
    freshness_score: float = Field(0.0, description="Data freshness score (0.0-1.0)")
    
    # Processing metadata
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="Extraction timestamp")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    
    # Related data
    portfolio_allocations: Dict[str, float] = Field(default_factory=dict, description="Portfolio allocations by risk profile")
    sector_breakdown: Dict[str, float] = Field(default_factory=dict, description="Sector allocation breakdown")
    
    # Analysis fields
    benchmark_comparison: Optional[Dict[str, float]] = Field(None, description="Comparison with benchmark")
    risk_metrics: Optional[Dict[str, float]] = Field(None, description="Risk analysis metrics")
    
    
class PortfolioAnalysis(BaseModel):
    """Analysis results for a portfolio."""
    
    # Portfolio summary
    total_funds: int = Field(..., description="Total number of funds")
    total_allocation: float = Field(..., description="Total allocation percentage")
    average_expense_ratio: Optional[float] = Field(None, description="Average expense ratio")
    
    # Risk profile breakdown
    risk_profile_allocations: Dict[str, float] = Field(default_factory=dict, description="Allocations by risk profile")
    asset_class_breakdown: Dict[str, float] = Field(default_factory=dict, description="Asset class distribution")
    
    # Quality scores
    overall_confidence: float = Field(0.0, description="Overall analysis confidence")
    data_completeness: float = Field(0.0, description="Data completeness score")
    
    # Insights
    recommendations: List[str] = Field(default_factory=list, description="Portfolio recommendations")
    warnings: List[str] = Field(default_factory=list, description="Potential issues")
    
    # Comparison data
    target_vs_actual: Dict[str, Dict[str, float]] = Field(default_factory=dict, description="Target vs actual allocations")
    drift_analysis: Dict[str, float] = Field(default_factory=dict, description="Allocation drift by fund")


class ProcessingSession(BaseModel):
    """Session data for processing workflow."""
    
    session_id: str = Field(..., description="Unique session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    
    # Input data
    input_file_path: Optional[str] = Field(None, description="Path to uploaded file")
    file_type: Literal["csv", "excel", "pdf", "json"] = Field(..., description="Input file type")
    
    # Processed data
    portfolio_items: List[PortfolioItem] = Field(default_factory=list, description="Parsed portfolio items")
    fund_extractions: Dict[str, ExtendedFundData] = Field(default_factory=dict, description="Extracted fund data by ticker")
    
    # Analysis results
    portfolio_analysis: Optional[PortfolioAnalysis] = Field(None, description="Portfolio analysis results")
    
    # Processing state
    stage: str = Field("idle", description="Current processing stage")
    progress: float = Field(0.0, description="Processing progress (0.0-1.0)")
    status: str = Field("idle", description="Processing status")
    
    # Chat context
    chat_history: List[Dict[str, str]] = Field(default_factory=list, description="Chat conversation history")
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences and selections")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    
    def update_progress(self, stage: str, progress: float, status: str = "processing"):
        """Update processing progress."""
        self.stage = stage
        self.progress = max(0.0, min(1.0, progress))
        self.status = status
        self.updated_at = datetime.utcnow()
    
    def add_chat_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a message to chat history."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        if metadata:
            message["metadata"] = metadata
        self.chat_history.append(message)
        self.updated_at = datetime.utcnow()
    
    def get_fund_by_ticker(self, ticker: str) -> Optional[ExtendedFundData]:
        """Get fund data by ticker."""
        return self.fund_extractions.get(ticker.upper())
    
    def add_fund_data(self, ticker: str, fund_data: ExtendedFundData):
        """Add extracted fund data."""
        self.fund_extractions[ticker.upper()] = fund_data
        self.updated_at = datetime.utcnow()


class DocumentSource(BaseModel):
    """Information about a source document."""
    
    url: Optional[str] = Field(None, description="Source URL")
    local_path: Optional[str] = Field(None, description="Local file path")
    document_type: str = Field(..., description="Type of document (prospectus, annual_report, etc.)")
    ticker: str = Field(..., description="Related fund ticker")
    
    # Metadata
    file_size: Optional[int] = Field(None, description="File size in bytes")
    download_date: Optional[datetime] = Field(None, description="When downloaded")
    last_modified: Optional[datetime] = Field(None, description="Last modification date")
    checksum: Optional[str] = Field(None, description="File checksum for integrity")
    
    # Source quality
    confidence: float = Field(0.0, description="Confidence in document authenticity")
    source_rating: Literal["official", "verified", "third_party", "unknown"] = Field("unknown", description="Source reliability")


class ExtractionResult(BaseModel):
    """Result from document extraction process."""
    
    source: DocumentSource = Field(..., description="Source document information")
    extracted_data: ExtendedFundData = Field(..., description="Extracted fund data")
    
    # Processing details
    processing_time: float = Field(..., description="Time taken for extraction")
    extraction_method: str = Field(..., description="Method used for extraction")
    
    # Quality metrics
    confidence_score: float = Field(..., description="Overall confidence in extraction")
    field_confidence: Dict[str, float] = Field(default_factory=dict, description="Confidence per field")
    
    # Issues and warnings
    warnings: List[str] = Field(default_factory=list, description="Extraction warnings")
    errors: List[str] = Field(default_factory=list, description="Extraction errors")
    
    # Human review requirements
    requires_review: bool = Field(False, description="Whether human review is needed")
    review_reasons: List[str] = Field(default_factory=list, description="Reasons for review")


class FundCategorization(BaseModel):
    """Categorization result for a fund."""
    
    # Basic identifiers
    ticker: str = Field(..., description="Fund ticker symbol")
    fund_name: str = Field(..., description="Fund name")
    
    # Primary classification
    asset_class: Literal["Equity", "Fixed Income", "Cash", "Alternatives"] = Field(..., description="Primary asset class")
    asset_class_confidence: float = Field(..., description="Confidence in asset class (0.0-1.0)")
    
    # Equity sub-classifications
    equity_region: Optional[Literal["US", "International", "Emerging", "Global"]] = Field(None, description="Geographic region for equity funds")
    equity_style: Optional[Literal["Value", "Growth", "Blend"]] = Field(None, description="Investment style for equity funds")
    equity_size: Optional[Literal["Large", "Mid", "Small", "Micro"]] = Field(None, description="Market cap focus for equity funds")
    
    # Fixed Income sub-classifications
    fixed_income_type: Optional[Literal["Government", "Corporate", "Municipal", "High Yield"]] = Field(None, description="Bond type for fixed income funds")
    fixed_income_duration: Optional[Literal["Short", "Intermediate", "Long"]] = Field(None, description="Duration focus for fixed income funds")
    
    # Research and classification metadata
    research_sources: List[str] = Field(default_factory=list, description="Sources used for classification")
    key_holdings: List[Dict[str, Any]] = Field(default_factory=list, description="Key fund holdings")
    expense_ratio: Optional[float] = Field(None, description="Fund expense ratio")
    morningstar_category: Optional[str] = Field(None, description="Morningstar category if available")
    
    # Classification process metadata
    classification_method: str = Field(..., description="Method used for classification")
    reasoning: str = Field(..., description="Human-readable explanation of classification")
    alternative_classifications: List[Dict[str, Any]] = Field(default_factory=list, description="Alternative classification suggestions")
    
    # Override tracking
    manual_override: bool = Field(False, description="Whether user manually overrode classification")
    override_reason: Optional[str] = Field(None, description="Reason for manual override")
    override_by: Optional[str] = Field(None, description="Who made the override")
    override_timestamp: Optional[datetime] = Field(None, description="When override was made")
    
    # Quality metrics
    data_completeness: float = Field(0.0, description="Completeness of available data (0.0-1.0)")
    classification_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When classification was made")
    
    def apply_override(self, new_asset_class: str, reason: str, override_by: str, **sub_categories):
        """Apply manual override to classification."""
        self.manual_override = True
        self.override_reason = reason
        self.override_by = override_by
        self.override_timestamp = datetime.utcnow()
        
        # Update classification
        self.asset_class = new_asset_class
        
        # Update sub-categories
        for key, value in sub_categories.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Lower confidence since it's manual
        self.asset_class_confidence = max(0.95, self.asset_class_confidence)


class CategorizationSession(BaseModel):
    """Session data for fund categorization workflow."""
    
    session_id: str = Field(..., description="Session identifier")
    portfolio_items: List[PortfolioItem] = Field(default_factory=list, description="Original portfolio items")
    
    # Categorization results
    fund_categorizations: Dict[str, FundCategorization] = Field(default_factory=dict, description="Categorizations by ticker")
    
    # Workflow state
    current_stage: Literal["uploaded", "researching", "classifying", "reviewing", "complete"] = Field("uploaded", description="Current workflow stage")
    funds_needing_input: List[str] = Field(default_factory=list, description="Tickers requiring user input")
    current_fund_index: int = Field(0, description="Index of fund currently being reviewed")
    
    # Interaction state
    pending_questions: List[Dict[str, Any]] = Field(default_factory=list, description="Questions waiting for user response")
    user_responses: List[Dict[str, Any]] = Field(default_factory=list, description="User responses to questions")
    
    # Session metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    
    # Progress tracking
    total_funds: int = Field(0, description="Total number of funds")
    categorized_funds: int = Field(0, description="Number of funds categorized")
    high_confidence_funds: int = Field(0, description="Number of high-confidence categorizations")
    
    def get_progress_percentage(self) -> float:
        """Get categorization progress as percentage."""
        if self.total_funds == 0:
            return 0.0
        return (self.categorized_funds / self.total_funds) * 100
    
    def get_fund_categorization(self, ticker: str) -> Optional[FundCategorization]:
        """Get categorization for a specific fund."""
        return self.fund_categorizations.get(ticker.upper())
    
    def add_fund_categorization(self, categorization: FundCategorization):
        """Add or update fund categorization."""
        self.fund_categorizations[categorization.ticker.upper()] = categorization
        self.categorized_funds = len(self.fund_categorizations)
        self.high_confidence_funds = len([c for c in self.fund_categorizations.values() if c.asset_class_confidence >= 0.8])
        self.updated_at = datetime.utcnow()
    
    def get_next_fund_needing_input(self) -> Optional[str]:
        """Get next fund ticker that needs user input."""
        if self.current_fund_index < len(self.funds_needing_input):
            return self.funds_needing_input[self.current_fund_index]
        return None
    
    def mark_current_fund_complete(self):
        """Mark current fund as complete and advance to next."""
        self.current_fund_index += 1
        self.updated_at = datetime.utcnow()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get categorization summary."""
        asset_class_counts = {}
        total_confidence = 0.0
        
        for categorization in self.fund_categorizations.values():
            asset_class = categorization.asset_class
            asset_class_counts[asset_class] = asset_class_counts.get(asset_class, 0) + 1
            total_confidence += categorization.asset_class_confidence
        
        avg_confidence = total_confidence / len(self.fund_categorizations) if self.fund_categorizations else 0.0
        
        return {
            "total_funds": self.total_funds,
            "categorized_funds": self.categorized_funds,
            "progress_percentage": self.get_progress_percentage(),
            "average_confidence": avg_confidence,
            "high_confidence_funds": self.high_confidence_funds,
            "asset_class_breakdown": asset_class_counts,
            "current_stage": self.current_stage,
            "needs_user_input": len(self.funds_needing_input),
            "is_complete": self.current_stage == "complete"
        }


class CategoryQuestion(BaseModel):
    """Question for user about fund categorization."""
    
    # Question metadata
    question_id: str = Field(..., description="Unique question identifier")
    ticker: str = Field(..., description="Fund ticker this question is about")
    fund_name: str = Field(..., description="Fund name for context")
    
    # Question content
    question_type: Literal["asset_class", "equity_region", "equity_style", "equity_size", "fixed_income_type", "fixed_income_duration"] = Field(..., description="Type of categorization question")
    question_text: str = Field(..., description="Human-readable question")
    
    # Answer options
    options: List[Dict[str, Any]] = Field(..., description="Available answer options")
    allow_custom: bool = Field(False, description="Whether custom answers are allowed")
    
    # Context information
    current_classification: Dict[str, Any] = Field(default_factory=dict, description="Current classification for context")
    confidence_score: Optional[float] = Field(None, description="Confidence in current classification")
    reasoning: Optional[str] = Field(None, description="Explanation of current classification")
    research_sources: List[str] = Field(default_factory=list, description="Research sources used")
    
    # Question metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When question was created")
    priority: int = Field(1, description="Question priority (1=high, 2=medium, 3=low)")
    
    def to_chat_message(self) -> Dict[str, Any]:
        """Convert to chat message format."""
        return {
            "type": "categorization_question",
            "question_id": self.question_id,
            "ticker": self.ticker,
            "fund_name": self.fund_name,
            "question": self.question_text,
            "options": self.options,
            "context": {
                "current_classification": self.current_classification,
                "confidence": self.confidence_score,
                "reasoning": self.reasoning
            },
            "metadata": {
                "question_type": self.question_type,
                "priority": self.priority,
                "allow_custom": self.allow_custom
            }
        }


class CategoryResponse(BaseModel):
    """User response to categorization question."""
    
    question_id: str = Field(..., description="ID of question being answered")
    ticker: str = Field(..., description="Fund ticker")
    
    # Response content
    selected_value: str = Field(..., description="Selected option value")
    custom_value: Optional[str] = Field(None, description="Custom value if provided")
    confidence: Optional[float] = Field(None, description="User's confidence in their answer")
    notes: Optional[str] = Field(None, description="Additional notes from user")
    
    # Response metadata
    response_time: float = Field(..., description="Time taken to respond in seconds")
    responded_at: datetime = Field(default_factory=datetime.utcnow, description="When response was given")
    
    def get_final_value(self) -> str:
        """Get the final value (custom if provided, otherwise selected)."""
        return self.custom_value if self.custom_value else self.selected_value


class ChatResponse(BaseModel):
    """Response from chat system."""
    
    message: str = Field(..., description="Chat message content")
    message_type: Literal["info", "question", "warning", "error", "success"] = Field("info", description="Message type")
    
    # Context
    session_id: str = Field(..., description="Session identifier")
    agent_type: str = Field(..., description="Responding agent")
    
    # Suggested actions
    suggested_actions: List[Dict[str, str]] = Field(default_factory=list, description="Suggested user actions")
    quick_replies: List[str] = Field(default_factory=list, description="Quick reply options")
    
    # Data attachments
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data payload")
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    confidence: float = Field(1.0, description="Confidence in response")


# Utility functions for data conversion
def portfolio_item_from_csv_row(row: Dict[str, str]) -> PortfolioItem:
    """Create PortfolioItem from CSV row data."""
    return PortfolioItem(
        ticker=row.get("Ticker", ""),
        name=row.get("Name", ""),
        asset_class=row.get("Asset Class", ""),
        expense_ratio=float(row.get("Expense Ratio (%)", 0)) if row.get("Expense Ratio (%)") else None,
        morningstar_category=row.get("Morningstar Category"),
        conservative_pct=float(row.get("Conservative (%)", 0)) if row.get("Conservative (%)") else None,
        mod_conservative_pct=float(row.get("Mod. Conservative (%)", 0)) if row.get("Mod. Conservative (%)") else None,
        moderate_pct=float(row.get("Moderate (%)", 0)) if row.get("Moderate (%)") else None,
        growth_pct=float(row.get("Growth (%)", 0)) if row.get("Growth (%)") else None,
        aggressive_pct=float(row.get("Aggressive (%)", 0)) if row.get("Aggressive (%)") else None,
    )


def extend_fund_data(original: OriginalFundData, ticker: str = None, **kwargs) -> ExtendedFundData:
    """Convert original FundData to ExtendedFundData with additional fields."""
    # Convert original to dict
    data = original.model_dump()
    
    # Add extended fields
    extended_fields = {
        "ticker": ticker,
        "data_source": kwargs.get("data_source", "pdf"),
        "extraction_method": kwargs.get("extraction_method", "llamaparse"),
        "confidence_score": kwargs.get("confidence_score", 0.8),
        **kwargs
    }
    
    data.update(extended_fields)
    return ExtendedFundData(**data)
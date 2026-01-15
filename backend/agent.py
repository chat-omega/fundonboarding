"""Agent wrapper for fund extraction with streaming support."""

import asyncio
import json
import os
import re
import uuid
from typing import AsyncGenerator, Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import pandas as pd

# Import existing extraction components
import sys
sys.path.append('..')
from config import config
from src.fund_extractor import FidelityFundExtraction, setup_extract_agent, aextract_data_over_splits
from src.split_detector import afind_categories_and_splits
from src.models import FundData, FundComparisonData
from llama_cloud_services import LlamaParse
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings


class EventType(str, Enum):
    """Event types for streaming updates."""
    TEXT = "text"
    STATUS = "status"
    PROGRESS = "progress"
    RESULTS = "results"
    ERROR = "error"
    TOOL_CALL = "tool_call"
    FUND_DISCOVERED = "fund_discovered"
    FUND_EXTRACTED = "fund_extracted"


@dataclass
class StreamEvent:
    """Event data structure for streaming."""
    type: EventType
    data: Dict[str, Any]
    timestamp: float = None
    message_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            import time
            self.timestamp = time.time()
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "messageId": self.message_id
        }


class FundExtractionAgent:
    """Agent for fund extraction with streaming capabilities."""
    
    def __init__(self):
        self.session_id = None
        self.llm = None
        self.parser = None
        self.extract_agent = None
        self.current_status = "idle"
        
        # Configuration from original project
        self.split_description = "Find and split by the main funds in this document, should be listed in the first few pages"
        self.split_rules = """
        - You must split by the name of the fund
        - Each fund will have a list of tables underneath it, like schedule of investments, financial statements
        - Each fund usually has schedule of investments right underneath it 
        - Do not tag the cover page/table of contents
        """
        self.split_key = "fidelity_asset_manager"
    
    async def initialize(self) -> AsyncGenerator[StreamEvent, None]:
        """Initialize the agent with required services."""
        yield StreamEvent(
            type=EventType.TEXT,
            data={"content": "🔧 Initializing Fund Extraction Agent..."}
        )
        
        try:
            # Validate configuration
            if not config.validate():
                raise Exception("Invalid API configuration")
            
            config.setup_environment()
            
            yield StreamEvent(
                type=EventType.STATUS,
                data={"stage": "models", "progress": 20, "message": "Setting up AI models..."}
            )
            
            # Set up models
            embed_model = OpenAIEmbedding(model_name="text-embedding-3-small")
            self.llm = OpenAI(
                model="gpt-4o",
                default_headers={},
                logprobs=False
            )
            Settings.llm = self.llm
            Settings.embed_model = embed_model
            
            yield StreamEvent(
                type=EventType.TEXT,
                data={"content": "✓ AI models initialized"}
            )
            
            yield StreamEvent(
                type=EventType.STATUS,
                data={"stage": "parser", "progress": 40, "message": "Setting up document parser..."}
            )
            
            # Set up parser
            self.parser = LlamaParse(
                premium_mode=True,
                result_type="markdown",
            )
            
            yield StreamEvent(
                type=EventType.TEXT,
                data={"content": "✓ LlamaParse initialized"}
            )
            
            yield StreamEvent(
                type=EventType.STATUS,
                data={"stage": "extractor", "progress": 60, "message": "Setting up data extractor..."}
            )
            
            # Set up extract agent
            self.extract_agent = setup_extract_agent()
            
            yield StreamEvent(
                type=EventType.TEXT,
                data={"content": "✓ LlamaExtract agent initialized"}
            )
            
            yield StreamEvent(
                type=EventType.STATUS,
                data={"stage": "ready", "progress": 100, "message": "Agent ready for extraction"}
            )
            
            self.current_status = "ready"
            
        except Exception as e:
            yield StreamEvent(
                type=EventType.ERROR,
                data={"message": f"Initialization failed: {str(e)}", "stage": "initialization"}
            )
            raise
    
    
    async def extract_from_pdf(self, file_path: str, message: str = None) -> AsyncGenerator[StreamEvent, None]:
        """Extract fund data from PDF with streaming updates."""
        
        self.session_id = str(uuid.uuid4())
        self.current_status = "processing"
        
        try:
            # Initialize if not ready
            if self.current_status != "ready":
                async for event in self.initialize():
                    yield event
            
            yield StreamEvent(
                type=EventType.TEXT,
                data={"content": f"📄 Processing PDF: {Path(file_path).name} with Docling + Gemini"}
            )
            
            # Handle S3 URLs by downloading file first
            local_file_path = file_path
            if file_path.startswith("https://") and (".s3." in file_path and "amazonaws.com" in file_path):
                try:
                    from utils.s3_storage import get_s3_storage
                    s3_storage = get_s3_storage()
                    
                    if s3_storage:
                        yield StreamEvent(
                            type=EventType.STATUS,
                            data={"stage": "downloading", "progress": 5, "message": "Downloading file from S3..."}
                        )
                        
                        # Download to temporary location
                        temp_dir = Path("/tmp/fund_processing")
                        temp_dir.mkdir(exist_ok=True)
                        local_file_path = str(temp_dir / f"temp_{self.session_id}.pdf")
                        
                        await s3_storage.download_file(file_path, local_file_path)
                        
                        yield StreamEvent(
                            type=EventType.TEXT,
                            data={"content": "✓ File downloaded from S3"}
                        )
                    else:
                        raise FileNotFoundError(f"S3 storage not available for file: {file_path}")
                        
                except Exception as e:
                    raise FileNotFoundError(f"Failed to download S3 file: {file_path} - {str(e)}")
            
            # Validate local file exists
            if not Path(local_file_path).exists():
                raise FileNotFoundError(f"PDF file not found: {local_file_path}")
            
            yield StreamEvent(
                type=EventType.STATUS,
                data={"stage": "extraction", "progress": 10, "message": "Starting fund extraction..."}
            )
            
            # Use unified extraction service with AI-powered classification and routing
            yield StreamEvent(
                type=EventType.STATUS,
                data={"stage": "classification", "progress": 20, "message": "Classifying document with AI..."}
            )
            
            from extraction_service import extraction_service
            result = await extraction_service.extract_fund(local_file_path, method='auto')
            
            if not result.success:
                raise Exception(f"Extraction failed: {result.error}")
            
            # Display classification result
            if result.classification_result:
                classification = result.classification_result
                yield StreamEvent(
                    type=EventType.TEXT,
                    data={"content": f"📋 Document classified as: {classification['document_type']} (confidence: {classification['confidence']:.2f})"}
                )
                if classification['reasoning']:
                    yield StreamEvent(
                        type=EventType.TEXT,
                        data={"content": f"💡 {classification['reasoning']}"}
                    )
            
            # Display warnings if any
            if result.warnings:
                for warning in result.warnings:
                    yield StreamEvent(
                        type=EventType.TEXT,
                        data={"content": f"⚠️ {warning}"}
                    )
            
            yield StreamEvent(
                type=EventType.STATUS,
                data={"stage": "extraction", "progress": 50, "message": f"Extracting with {result.method_used}..."}
            )
            
            # Handle both single and multi-fund results
            if isinstance(result.fund_data, list):
                # Multi-fund result
                fund_results = result.fund_data
                total_funds = len(fund_results)
                
                yield StreamEvent(
                    type=EventType.TEXT,
                    data={"content": f"✓ Extracted {total_funds} funds using {result.method_used}"}
                )
                
                # Stream individual fund extraction events
                for i, fund in enumerate(fund_results):
                    yield StreamEvent(
                        type=EventType.FUND_EXTRACTED,
                        data={
                            "fund": fund.dict(),
                            "index": i,
                            "total": total_funds
                        }
                    )
                    
                    yield StreamEvent(
                        type=EventType.TEXT,
                        data={"content": f"  • {fund.fund_name}"}
                    )
                
                all_fund_data = FundComparisonData(funds=fund_results)
                single_fund_processed = True
                
            else:
                # Single fund result
                fund_results = [result.fund_data] if result.fund_data else []
                
                if fund_results:
                    yield StreamEvent(
                        type=EventType.FUND_EXTRACTED,
                        data={
                            "fund": fund_results[0].dict(),
                            "index": 0,
                            "total": 1
                        }
                    )
                    
                    yield StreamEvent(
                        type=EventType.TEXT,
                        data={"content": f"✓ Extracted single fund: {fund_results[0].fund_name}"}
                    )
                    
                    all_fund_data = FundComparisonData(funds=fund_results)
                else:
                    raise Exception("No fund data extracted")
                
                single_fund_processed = True
            
            # Prepare fund results for analysis (all extraction is done by unified service)
            fund_results = [fund.dict() for fund in all_fund_data.funds]
            
            yield StreamEvent(
                type=EventType.STATUS,
                data={"stage": "analysis", "progress": 90, "message": "Performing analysis..."}
            )
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame([fund.dict() for fund in all_fund_data.funds])
            
            # Add analysis calculations
            analysis_data = self._perform_analysis(df)
            
            yield StreamEvent(
                type=EventType.STATUS,
                data={"stage": "complete", "progress": 100, "message": "Extraction completed!"}
            )
            
            # Final results
            yield StreamEvent(
                type=EventType.RESULTS,
                data={
                    "funds": fund_results,
                    "analysis": analysis_data,
                    "summary": {
                        "total_funds": len(all_fund_data.funds),
                        "extraction_method": result.method_used,
                        "document_type": result.document_type or "unknown",
                        "confidence_score": result.confidence_score,
                        "session_id": self.session_id
                    },
                    "metadata": {
                        "source_file": str(Path(file_path).name),
                        "extraction_time": pd.Timestamp.now().isoformat(),
                        "classification": result.classification_result
                    }
                }
            )
            
            yield StreamEvent(
                type=EventType.TEXT,
                data={"content": "🎉 Fund extraction completed successfully!"}
            )
            
            # Cleanup temporary file if it was downloaded from S3
            if local_file_path != file_path and Path(local_file_path).exists():
                try:
                    os.remove(local_file_path)
                    yield StreamEvent(
                        type=EventType.TEXT,
                        data={"content": "✓ Temporary file cleaned up"}
                    )
                except Exception:
                    pass  # Ignore cleanup errors
            
            self.current_status = "completed"
            
        except Exception as e:
            yield StreamEvent(
                type=EventType.ERROR,
                data={
                    "message": str(e),
                    "stage": "extraction",
                    "session_id": self.session_id
                }
            )
            self.current_status = "error"
            raise
    
    def _perform_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Perform analysis on extracted fund data."""
        analysis = {}
        
        try:
            # Return per risk calculation
            if 'one_year_return' in df.columns and 'equity_pct' in df.columns:
                df["return_per_risk"] = df["one_year_return"] / df["equity_pct"]
                analysis["return_per_risk"] = df["return_per_risk"].to_dict()
            
            # Allocation drift calculation
            if 'equity_pct' in df.columns and 'target_equity_pct' in df.columns:
                df["drift"] = df["equity_pct"] - df["target_equity_pct"]
                analysis["allocation_drift"] = df["drift"].to_dict()
            
            # Performance metrics
            if 'one_year_return' in df.columns:
                analysis["performance_stats"] = {
                    "mean_return": float(df["one_year_return"].mean()),
                    "max_return": float(df["one_year_return"].max()),
                    "min_return": float(df["one_year_return"].min()),
                    "std_return": float(df["one_year_return"].std())
                }
            
            # Expense ratio analysis
            if 'expense_ratio' in df.columns:
                analysis["expense_stats"] = {
                    "mean_expense": float(df["expense_ratio"].mean()),
                    "max_expense": float(df["expense_ratio"].max()),
                    "min_expense": float(df["expense_ratio"].min())
                }
            
            # Asset allocation summary
            allocation_columns = ['equity_pct', 'fixed_income_pct', 'money_market_pct', 'other_pct']
            existing_cols = [col for col in allocation_columns if col in df.columns]
            if existing_cols:
                analysis["allocation_summary"] = {}
                for col in existing_cols:
                    analysis["allocation_summary"][col] = {
                        "mean": float(df[col].mean()),
                        "range": [float(df[col].min()), float(df[col].max())]
                    }
            
        except Exception as e:
            analysis["error"] = f"Analysis failed: {str(e)}"
        
        return analysis
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "status": self.current_status,
            "session_id": self.session_id,
            "initialized": self.llm is not None
        }
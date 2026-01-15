"""Portfolio Intake Agent for processing CSV/Excel portfolio data."""

import pandas as pd
import csv
from typing import AsyncGenerator, Dict, List, Optional
from pathlib import Path
import asyncio
import tempfile

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent, AgentType, AgentMessage, MessageType
from models.unified_models import PortfolioItem, ProcessingSession, portfolio_item_from_csv_row
# Temporarily disable tracing imports


class PortfolioIntakeAgent(BaseAgent):
    """Agent responsible for processing portfolio data from CSV/Excel files."""
    
    def __init__(self, session_id: str):
        super().__init__(AgentType.INTAKE, session_id)
        self.supported_formats = ['.csv', '.xlsx', '.xls']
        
    async def _setup(self) -> None:
        """Initialize the intake agent."""
        self.set_confidence_score("file_reading", 0.95)
        
    async def _cleanup(self) -> None:
        """Cleanup resources."""
        pass
        
    async def process(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Process portfolio data from uploaded file."""
        
        if message.type == MessageType.REQUEST_ACTION and "file_path" in message.data:
            file_path = message.data["file_path"]
            
            # Emit status update
            yield await self.emit_status("processing_file", {
                "file_path": file_path,
                "stage": "reading"
            })
            
            try:
                # Process the file based on extension
                portfolio_items = await self._process_file(file_path)
                
                # Update confidence based on data quality
                confidence = self._calculate_confidence(portfolio_items)
                self.set_confidence_score("portfolio_parsing", confidence)
                
                # Emit results
                yield self.create_message(
                    message_type=MessageType.DATA_PROCESSED,
                    recipient=AgentType.RESEARCH,  # Next agent in pipeline
                    data={
                        "portfolio_items": [item.model_dump() for item in portfolio_items],
                        "confidence_score": confidence,
                        "total_funds": len(portfolio_items),
                        "file_processed": file_path
                    }
                )
                
                # Update processing context
                if self.context:
                    self.context.portfolio_items = portfolio_items
                    self.update_context({
                        "processing_stage": "portfolio_parsed",
                        "portfolio_data": {"items": [item.model_dump() for item in portfolio_items]}
                    })
                
            except Exception as e:
                yield await self.emit_error(f"Failed to process portfolio file: {str(e)}", {
                    "file_path": file_path,
                    "error_type": type(e).__name__
                })
    
    async def _process_file(self, file_path: str) -> List[PortfolioItem]:
        """Process a CSV or Excel file and extract portfolio items."""
        local_file_path = file_path
        temp_file_path = None
        
        try:
            # Handle S3 URLs by downloading file first
            if file_path.startswith("https://") and (".s3." in file_path and "amazonaws.com" in file_path):
                try:
                    from utils.s3_storage import get_s3_storage
                    s3_storage = get_s3_storage()
                    
                    if s3_storage:
                        # Create temporary file
                        temp_dir = tempfile.mkdtemp()
                        filename = Path(file_path.split('/')[-1])  # Extract filename from URL
                        temp_file_path = Path(temp_dir) / filename
                        local_file_path = str(temp_file_path)
                        
                        # Download from S3
                        await s3_storage.download_file(file_path, local_file_path)
                    else:
                        raise FileNotFoundError(f"S3 storage not available for file: {file_path}")
                        
                except Exception as e:
                    raise FileNotFoundError(f"Failed to download S3 file: {file_path} - {str(e)}")
            
            # Validate local file exists
            path = Path(local_file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {local_file_path}")
                
            if path.suffix not in self.supported_formats:
                raise ValueError(f"Unsupported file format: {path.suffix}")
                
            # Read the file based on format
            if path.suffix == '.csv':
                return await self._process_csv(local_file_path)
            else:
                return await self._process_excel(local_file_path)
                
        finally:
            # Clean up temporary file if it was created
            if temp_file_path and temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                    temp_file_path.parent.rmdir()  # Remove temp directory if empty
                except Exception:
                    pass  # Ignore cleanup errors
    
    async def _process_csv(self, file_path: str) -> List[PortfolioItem]:
        """Process CSV file."""
        portfolio_items = []
        
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-8-sig', 'iso-8859-1', 'cp1252']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ValueError("Unable to read CSV file with any supported encoding")
            
            # Process each row
            for _, row in df.iterrows():
                try:
                    # Convert pandas Series to dict
                    row_dict = row.to_dict()
                    
                    # Clean up any NaN values
                    clean_row = {}
                    for key, value in row_dict.items():
                        if pd.isna(value):
                            clean_row[key] = None
                        else:
                            clean_row[key] = str(value) if not isinstance(value, str) else value
                    
                    # Create portfolio item
                    portfolio_item = portfolio_item_from_csv_row(clean_row)
                    
                    # Validate required fields
                    if portfolio_item.ticker and portfolio_item.name:
                        portfolio_items.append(portfolio_item)
                    
                except Exception as e:
                    # Log warning but continue processing other rows
                    print(f"Warning: Failed to process row {row.name}: {e}")
                    continue
            
        except Exception as e:
            raise ValueError(f"Failed to process CSV file: {str(e)}")
            
        if not portfolio_items:
            raise ValueError("No valid portfolio items found in CSV file")
            
        return portfolio_items
    
    async def _process_excel(self, file_path: str) -> List[PortfolioItem]:
        """Process Excel file."""
        portfolio_items = []
        
        try:
            # Read Excel file (try first sheet)
            df = pd.read_excel(file_path, sheet_name=0)
            
            # Process each row similar to CSV
            for _, row in df.iterrows():
                try:
                    row_dict = row.to_dict()
                    
                    # Clean up NaN values
                    clean_row = {}
                    for key, value in row_dict.items():
                        if pd.isna(value):
                            clean_row[key] = None
                        else:
                            clean_row[key] = str(value) if not isinstance(value, str) else value
                    
                    portfolio_item = portfolio_item_from_csv_row(clean_row)
                    
                    if portfolio_item.ticker and portfolio_item.name:
                        portfolio_items.append(portfolio_item)
                        
                except Exception as e:
                    print(f"Warning: Failed to process Excel row {row.name}: {e}")
                    continue
                    
        except Exception as e:
            raise ValueError(f"Failed to process Excel file: {str(e)}")
            
        if not portfolio_items:
            raise ValueError("No valid portfolio items found in Excel file")
            
        return portfolio_items
    
    def _calculate_confidence(self, portfolio_items: List[PortfolioItem]) -> float:
        """Calculate confidence score for portfolio parsing."""
        if not portfolio_items:
            return 0.0
            
        total_score = 0.0
        factors = {
            'has_ticker': 0.3,
            'has_name': 0.2,
            'has_asset_class': 0.2,
            'has_expense_ratio': 0.1,
            'has_allocations': 0.2
        }
        
        for item in portfolio_items:
            item_score = 0.0
            
            # Check required fields
            if item.ticker and item.ticker.strip():
                item_score += factors['has_ticker']
            if item.name and item.name.strip():
                item_score += factors['has_name']
            if item.asset_class and item.asset_class.strip():
                item_score += factors['has_asset_class']
            if item.expense_ratio is not None:
                item_score += factors['has_expense_ratio']
                
            # Check if has any allocation data
            allocations = [
                item.conservative_pct,
                item.mod_conservative_pct,
                item.moderate_pct,
                item.growth_pct,
                item.aggressive_pct
            ]
            if any(alloc is not None and alloc > 0 for alloc in allocations):
                item_score += factors['has_allocations']
                
            total_score += item_score
            
        return total_score / len(portfolio_items)
    
    def detect_file_structure(self, file_path: str) -> Dict[str, any]:
        """Analyze file structure to understand the data format."""
        try:
            # Read first few rows to understand structure
            if file_path.endswith('.csv'):
                df_sample = pd.read_csv(file_path, nrows=5)
            else:
                df_sample = pd.read_excel(file_path, nrows=5)
            
            analysis = {
                "columns": list(df_sample.columns),
                "row_count_sample": len(df_sample),
                "has_ticker": any("ticker" in col.lower() for col in df_sample.columns),
                "has_name": any("name" in col.lower() for col in df_sample.columns),
                "has_allocations": any("%" in col for col in df_sample.columns),
                "detected_format": "model_portfolio" if "Conservative" in df_sample.columns else "unknown"
            }
            
            return analysis
            
        except Exception as e:
            return {"error": str(e), "columns": []}
    
    async def generate_chat_response(self, portfolio_items: List[PortfolioItem]) -> str:
        """Generate a chat response describing the processed portfolio."""
        if not portfolio_items:
            return "I couldn't find any valid portfolio items in your file. Please check the format and try again."
        
        # Analyze the portfolio
        total_funds = len(portfolio_items)
        asset_classes = set(item.asset_class for item in portfolio_items if item.asset_class)
        tickers = [item.ticker for item in portfolio_items if item.ticker]
        
        # Generate response
        response_parts = [
            f"Great! I've processed your portfolio and found **{total_funds} funds**."
        ]
        
        if asset_classes:
            response_parts.append(f"Your portfolio spans {len(asset_classes)} asset classes: {', '.join(asset_classes)}.")
        
        if tickers:
            response_parts.append(f"The funds include: {', '.join(tickers[:5])}")
            if len(tickers) > 5:
                response_parts.append(f"and {len(tickers) - 5} more.")
        
        response_parts.append("Should I now research and extract detailed information from the fund prospectuses?")
        
        return " ".join(response_parts)


class CSVAnalyzer:
    """Helper class to analyze CSV structure and content."""
    
    @staticmethod
    def detect_delimiter(file_path: str) -> str:
        """Detect the CSV delimiter."""
        with open(file_path, 'r', encoding='utf-8') as f:
            sample = f.read(1024)
            
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(sample).delimiter
        return delimiter
    
    @staticmethod
    def validate_portfolio_format(df: pd.DataFrame) -> Dict[str, bool]:
        """Validate if DataFrame matches expected portfolio format."""
        required_cols = ['ticker', 'name']
        optional_cols = ['asset class', 'expense ratio', 'conservative', 'moderate', 'growth']
        
        # Normalize column names for comparison
        df_cols_lower = [col.lower() for col in df.columns]
        
        validation = {
            'has_ticker': any('ticker' in col for col in df_cols_lower),
            'has_name': any('name' in col for col in df_cols_lower),
            'has_asset_class': any('asset' in col for col in df_cols_lower),
            'has_allocations': any('%' in col for col in df.columns),
            'is_valid_portfolio': False
        }
        
        # Check if it's a valid portfolio format
        validation['is_valid_portfolio'] = (
            validation['has_ticker'] and 
            validation['has_name'] and
            len(df) > 0
        )
        
        return validation
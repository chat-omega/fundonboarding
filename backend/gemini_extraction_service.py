"""
Gemini-based fund extraction service using Docling for document parsing.
Replaces complex LlamaParse + splitting with single-pass extraction.
"""

import asyncio
import json
import os
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from abc import ABC, abstractmethod
import pandas as pd
import re

# Fix environment variables BEFORE importing Docling to avoid permission issues
# Use appropriate HOME directory
if not os.path.exists('/app'):
    os.environ['HOME'] = os.path.expanduser('~')
else:
    os.environ['HOME'] = '/app'
os.environ['TMPDIR'] = '/tmp'
os.environ['XDG_CACHE_HOME'] = '/tmp/docling_cache'
os.environ['XDG_DATA_HOME'] = '/tmp/docling_data'

# Ensure temp directories exist
os.makedirs('/tmp/docling_cache', exist_ok=True)
os.makedirs('/tmp/docling_data', exist_ok=True)

try:
    from google import genai
    from google.genai.types import GenerateContentConfig
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None
    GenerateContentConfig = None

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    DocumentConverter = None

from pydantic import BaseModel

import sys
sys.path.append('..')
from src.models import FundData
from config import config


class GeminiExtractionResult(BaseModel):
    """Result of Gemini-based fund extraction."""
    success: bool
    fund_data: Optional[FundData] = None
    error: Optional[str] = None
    method_used: str = "gemini_docling"
    extraction_time: float
    confidence_score: float = 0.0
    markdown_length: int = 0
    tables_extracted: int = 0
    warnings: List[str] = []


class DocumentParsingResult(BaseModel):
    """Result of document parsing with Docling."""
    success: bool
    markdown_content: str = ""
    tables_markdown: List[str] = []
    page_count: int = 0
    error: Optional[str] = None
    warnings: List[str] = []


class DoclingParser:
    """Document parser using Docling for PDF to markdown conversion."""
    
    def __init__(self):
        self.converter = None
        self._initialized = False
    
    def _initialize(self):
        """Initialize Docling converter."""
        if self._initialized:
            return
        
        if not DOCLING_AVAILABLE:
            raise ImportError("Docling not available. Install with: pip install docling")
        
        self.converter = DocumentConverter()
        self._initialized = True
    
    def parse_document(self, pdf_path: str) -> DocumentParsingResult:
        """Parse PDF document to markdown with table extraction."""
        try:
            self._initialize()
            
            # Convert document
            result = self.converter.convert(pdf_path)
            
            # Extract main markdown content
            markdown_content = result.document.export_to_markdown()
            
            # Extract tables as separate markdown
            tables_markdown = []
            for table_idx, table in enumerate(result.document.tables):
                try:
                    # Get table as pandas DataFrame then convert to markdown
                    table_df = table.export_to_dataframe()
                    if not table_df.empty:
                        table_md = table_df.to_markdown(index=False)
                        tables_markdown.append(f"## Table {table_idx + 1}\n{table_md}")
                except Exception as e:
                    # Fallback: try to get table as HTML and note the issue
                    tables_markdown.append(f"## Table {table_idx + 1}\n*Table extraction error: {str(e)}*")
            
            # Get page count (estimate from markdown content)
            page_count = markdown_content.count('---') + 1  # Page breaks in markdown
            
            return DocumentParsingResult(
                success=True,
                markdown_content=markdown_content,
                tables_markdown=tables_markdown,
                page_count=page_count
            )
            
        except Exception as e:
            return DocumentParsingResult(
                success=False,
                error=f"Document parsing failed: {str(e)}"
            )


class GeminiExtractor:
    """Fund data extractor using Google Gemini models."""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.client = None
        self._initialized = False
    
    def _initialize(self):
        """Initialize Gemini client."""
        if self._initialized:
            return
        
        if not GEMINI_AVAILABLE:
            raise ImportError("Google GenAI not available. Install with: pip install google-genai")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=self.api_key)
        self._initialized = True
    
    def _create_extraction_prompt(self, markdown_content: str, tables_markdown: List[str], pdf_filename: str) -> str:
        """Create structured prompt for fund data extraction."""
        
        # Get filename for potential ticker/name hints
        filename_stem = Path(pdf_filename).stem.upper()
        
        # Combine tables with main content
        tables_section = ""
        if tables_markdown:
            tables_section = "\n\n## EXTRACTED TABLES:\n" + "\n\n".join(tables_markdown)
        
        prompt = f"""
You are a financial document analyst. Extract fund information from this ETF factsheet or fund document.

DOCUMENT FILENAME: {filename_stem}

DOCUMENT CONTENT:
{markdown_content}

{tables_section}

Extract the following information and return ONLY a valid JSON object with these exact fields:

{{
    "fund_name": "Full fund name as it appears in document",
    "ticker": "Ticker symbol if available (e.g. VTI, VTV, VUG)",
    "fund_type": "Type of fund (ETF, Mutual Fund, Index Fund, etc.)",
    "target_equity_pct": "Target equity percentage from fund name if applicable (e.g. 20, 30, 40, 50, 60, 70, 85) or null",
    "report_date": "Report date in YYYY-MM-DD format or null",
    "inception_date": "Fund inception date in YYYY-MM-DD format or null",
    
    // Asset Allocation
    "equity_pct": "Current equity allocation percentage (0-100) or null",
    "fixed_income_pct": "Fixed income allocation percentage (0-100) or null", 
    "money_market_pct": "Money market/cash allocation percentage (0-100) or null",
    "other_pct": "Other investments percentage or null",
    
    // Financial Metrics
    "nav": "Net Asset Value per share as number or null",
    "net_assets_usd": "Total net assets in USD as number or null",
    "expense_ratio": "Expense ratio as percentage (e.g. 0.03 for 0.03%) or null",
    "management_fee": "Management fee as percentage or null",
    "minimum_investment": "Minimum initial investment amount in USD or null",
    
    // ETF-specific fields
    "shares_outstanding": "Number of shares outstanding for ETFs or null",
    "market_price": "Market price per share for ETFs or null", 
    "premium_discount": "Premium/discount percentage relative to NAV for ETFs or null",
    "bid_ask_spread": "Bid-ask spread for ETF trading or null",
    "dividend_yield": "Dividend yield percentage or null",
    "distribution_frequency": "Distribution frequency (Monthly, Quarterly, Annually, etc.) or null",
    
    // Performance
    "one_year_return": "One-year return as percentage or null",
    "portfolio_turnover": "Portfolio turnover rate as percentage or null",
    
    // Holdings Information
    "number_of_holdings": "Total number of holdings as integer or null",
    "top_10_holdings": ["List of top 10 holdings with percentages as strings"] or null,
    "sector_allocation": ["List of sector allocations with percentages as strings"] or null,
    "geographic_allocation": ["List of geographic/country allocations with percentages as strings"] or null,
    
    // Additional Information  
    "fund_manager": "Fund manager or management team or null",
    "management_company": "Management company or fund family or null",
    "benchmark": "Primary benchmark index or null",
    "investment_objective": "Fund's investment objective or strategy description or null",
    
    // Risk and Flow Metrics
    "equity_futures_notional": "Net equity futures notional amount in USD or null",
    "bond_futures_notional": "Net bond futures notional amount in USD or null",
    "net_investment_income": "Net investment income in USD or null",
    "total_distributions": "Total distributions to shareholders in USD or null",
    "net_asset_change": "Net change in assets for the period in USD or null"
}}

IMPORTANT EXTRACTION RULES:
1. Extract numeric values as numbers, not strings
2. Convert percentages to decimal format (e.g. "0.03%" becomes 0.03)
3. Use null for missing values, never use empty strings or "N/A"
4. If ticker not found in document, try using filename: {filename_stem}
5. Focus on the main retail share class data
6. Look carefully in tables, financial highlights, portfolio composition, and holdings sections
7. For ETFs, look for NAV in "Net Asset Value" sections and inception date in fund profile
8. Extract top holdings with their percentage weights if shown in tables
9. Extract sector allocation data from pie charts or allocation tables
10. Look for dividend/distribution information in performance or distribution sections
11. For holdings count, look for "Number of Holdings" or similar metrics
12. Return ONLY the JSON object, no additional text or markdown

JSON:"""

        return prompt
    
    async def extract_fund_data(self, markdown_content: str, tables_markdown: List[str], pdf_filename: str) -> Dict[str, Any]:
        """Extract fund data using Gemini with full document context."""
        self._initialize()
        
        prompt = self._create_extraction_prompt(markdown_content, tables_markdown, pdf_filename)
        
        # Configure generation settings
        config = GenerateContentConfig(
            temperature=0.1,  # Low temperature for consistent extraction
            max_output_tokens=4096,
            top_p=0.95,
        )
        
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=config
            )
            
            response_text = response.text.strip()
            
            # Try to parse JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                fund_dict = json.loads(json_str)
                return fund_dict
            else:
                # Fallback: try to parse entire response as JSON
                return json.loads(response_text)
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in Gemini response: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {str(e)}")


class GeminiExtractionService:
    """Main service combining Docling parsing with Gemini extraction."""
    
    def __init__(self, gemini_api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        self.parser = DoclingParser()
        self.extractor = GeminiExtractor(gemini_api_key, model_name)
    
    def _calculate_confidence_score(self, fund_data: FundData, parsing_result: DocumentParsingResult) -> float:
        """Calculate confidence score based on fund type and extracted data completeness."""
        if not fund_data:
            return 0.0
        
        fields = fund_data.model_dump()
        fund_type = getattr(fund_data, 'fund_type', '').upper() if fund_data.fund_type else ''
        
        # Define relevant fields by fund type
        if 'ETF' in fund_type:
            # ETF-focused scoring
            core_fields = ['fund_name', 'ticker', 'nav', 'expense_ratio', 'net_assets_usd']
            important_fields = ['one_year_return', 'portfolio_turnover', 'number_of_holdings', 'inception_date']
            etf_fields = ['dividend_yield', 'top_10_holdings', 'sector_allocation', 'shares_outstanding']
            less_relevant = ['target_equity_pct', 'minimum_investment', 'bond_futures_notional']
        else:
            # Mutual Fund focused scoring
            core_fields = ['fund_name', 'nav', 'expense_ratio', 'net_assets_usd', 'minimum_investment']
            important_fields = ['one_year_return', 'portfolio_turnover', 'target_equity_pct', 'inception_date']
            etf_fields = ['management_fee', 'net_investment_income', 'total_distributions']
            less_relevant = ['shares_outstanding', 'market_price', 'premium_discount', 'bid_ask_spread']
        
        # Calculate scores for each category
        core_score = sum(1 for field in core_fields if fields.get(field) is not None) / len(core_fields)
        important_score = sum(1 for field in important_fields if fields.get(field) is not None) / len(important_fields)
        specific_score = sum(1 for field in etf_fields if fields.get(field) is not None) / len(etf_fields)
        
        # Don't penalize for missing less relevant fields
        relevant_fields = set(core_fields + important_fields + etf_fields)
        total_relevant = len(relevant_fields)
        filled_relevant = sum(1 for field in relevant_fields if fields.get(field) is not None)
        
        # Weighted confidence calculation
        confidence = (
            core_score * 0.5 +           # 50% weight on core fields
            important_score * 0.3 +      # 30% weight on important fields  
            specific_score * 0.2         # 20% weight on fund-type specific fields
        )
        
        # Bonus for having lists populated (holdings, sectors)
        list_fields = ['top_10_holdings', 'sector_allocation', 'geographic_allocation']
        list_bonus = sum(0.05 for field in list_fields if fields.get(field) and len(fields[field]) > 0)
        
        # Bonus for complete allocation data
        allocation_fields = ['equity_pct', 'fixed_income_pct', 'money_market_pct']
        allocation_complete = sum(1 for field in allocation_fields if fields.get(field) is not None)
        allocation_bonus = 0.1 if allocation_complete >= 2 else 0.0
        
        # Small parsing penalty
        parsing_penalty = 0.05 if parsing_result.warnings else 0.0
        
        final_score = confidence + list_bonus + allocation_bonus - parsing_penalty
        return min(1.0, max(0.0, final_score))
    
    def _add_filename_fallbacks(self, fund_dict: Dict[str, Any], pdf_path: str) -> Dict[str, Any]:
        """Add fallback data based on filename analysis."""
        filename = Path(pdf_path).stem.upper()
        
        # Add ticker if missing
        if not fund_dict.get('ticker') and filename:
            # Check if filename looks like a ticker (2-5 uppercase letters)
            if re.match(r'^[A-Z]{2,5}$', filename):
                fund_dict['ticker'] = filename
        
        # Add fund name if missing
        if not fund_dict.get('fund_name'):
            ticker_to_name = {
                "VTI": "Vanguard Total Stock Market ETF",
                "VTV": "Vanguard Value ETF", 
                "VUG": "Vanguard Growth ETF",
                "IVV": "iShares Core S&P 500 ETF",
                "IEFA": "iShares Core MSCI EAFE ETF"
            }
            fund_dict['fund_name'] = ticker_to_name.get(filename, f"{filename} Fund")
        
        # Set default fund type if missing but we have indicators
        if not fund_dict.get('fund_type'):
            if fund_dict.get('ticker') or 'ETF' in fund_dict.get('fund_name', ''):
                fund_dict['fund_type'] = "ETF"
        
        return fund_dict
    
    def _validate_and_enrich_data(self, fund_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and enrich extracted fund data."""
        # Validate expense ratios (should be small percentages)
        if fund_dict.get('expense_ratio') and fund_dict['expense_ratio'] > 5:
            # Likely extracted as whole number instead of decimal
            fund_dict['expense_ratio'] = fund_dict['expense_ratio'] / 100
        
        # Validate one year return (convert to percentage if needed)
        if fund_dict.get('one_year_return'):
            if fund_dict['one_year_return'] > 0 and fund_dict['one_year_return'] < 1:
                # Convert decimal to percentage
                fund_dict['one_year_return'] = fund_dict['one_year_return'] * 100
        
        # Enrich fund type based on ticker patterns
        if fund_dict.get('ticker') and not fund_dict.get('fund_type'):
            ticker = fund_dict['ticker'].upper()
            if ticker.endswith(('I', 'T')):  # Common ETF patterns
                fund_dict['fund_type'] = 'ETF'
        
        # Calculate other_pct if allocation percentages are provided
        allocation_fields = ['equity_pct', 'fixed_income_pct', 'money_market_pct']
        allocations = [fund_dict.get(field, 0) for field in allocation_fields if fund_dict.get(field) is not None]
        if len(allocations) >= 2:
            total_allocation = sum(allocations)
            if 95 <= total_allocation <= 105:  # Close to 100%
                fund_dict['other_pct'] = max(0, 100 - total_allocation)
        
        # Infer distribution frequency for ETFs
        if fund_dict.get('fund_type') == 'ETF' and fund_dict.get('dividend_yield') and not fund_dict.get('distribution_frequency'):
            fund_dict['distribution_frequency'] = 'Quarterly'  # Most common for ETFs
        
        # Clean up string fields
        string_fields = ['fund_name', 'management_company', 'fund_manager', 'benchmark', 'investment_objective']
        for field in string_fields:
            if fund_dict.get(field):
                # Remove extra whitespace and common artifacts
                value = str(fund_dict[field]).strip()
                value = re.sub(r'\s+', ' ', value)  # Normalize whitespace
                value = re.sub(r'[^\w\s\-\.\,\%\(\)®™&]', '', value)  # Remove unusual chars
                fund_dict[field] = value[:500] if len(value) > 500 else value  # Truncate long descriptions
        
        # Clean up list fields
        list_fields = ['top_10_holdings', 'sector_allocation', 'geographic_allocation']
        for field in list_fields:
            if fund_dict.get(field) and isinstance(fund_dict[field], list):
                # Clean and deduplicate
                cleaned_list = []
                for item in fund_dict[field]:
                    if isinstance(item, str):
                        clean_item = item.strip()
                        if clean_item and clean_item not in cleaned_list:
                            cleaned_list.append(clean_item)
                fund_dict[field] = cleaned_list[:20]  # Limit to 20 items max
        
        return fund_dict
    
    async def extract_fund(self, pdf_path: str) -> GeminiExtractionResult:
        """Extract fund data from PDF using Docling + Gemini."""
        start_time = time.time()
        warnings = []
        
        try:
            # Step 1: Parse document with Docling
            parsing_result = self.parser.parse_document(pdf_path)
            
            if not parsing_result.success:
                return GeminiExtractionResult(
                    success=False,
                    error=f"Document parsing failed: {parsing_result.error}",
                    extraction_time=time.time() - start_time
                )
            
            warnings.extend(parsing_result.warnings)
            
            # Step 2: Extract fund data with Gemini
            fund_dict = await self.extractor.extract_fund_data(
                parsing_result.markdown_content,
                parsing_result.tables_markdown,
                pdf_path
            )
            
            # Step 3: Add filename-based fallbacks
            fund_dict = self._add_filename_fallbacks(fund_dict, pdf_path)
            
            # Step 4: Validate and enrich data
            fund_dict = self._validate_and_enrich_data(fund_dict)
            
            # Step 5: Create FundData object
            fund_data = FundData(**fund_dict)
            
            # Step 5: Calculate confidence score
            confidence_score = self._calculate_confidence_score(fund_data, parsing_result)
            
            extraction_time = time.time() - start_time
            
            return GeminiExtractionResult(
                success=True,
                fund_data=fund_data,
                extraction_time=extraction_time,
                confidence_score=confidence_score,
                markdown_length=len(parsing_result.markdown_content),
                tables_extracted=len(parsing_result.tables_markdown),
                warnings=warnings
            )
            
        except Exception as e:
            extraction_time = time.time() - start_time
            return GeminiExtractionResult(
                success=False,
                error=f"Extraction failed: {str(e)}",
                extraction_time=extraction_time,
                warnings=warnings
            )
    
    async def extract_multiple_funds(self, pdf_paths: List[str]) -> List[GeminiExtractionResult]:
        """Extract multiple funds in parallel."""
        tasks = [self.extract_fund(path) for path in pdf_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(GeminiExtractionResult(
                    success=False,
                    error=str(result),
                    extraction_time=0.0
                ))
            else:
                final_results.append(result)
        
        return final_results


# Global service instance
gemini_extraction_service = GeminiExtractionService()


def check_dependencies() -> Dict[str, bool]:
    """Check if required dependencies are available."""
    return {
        "docling": DOCLING_AVAILABLE,
        "google_genai": GEMINI_AVAILABLE,
        "gemini_api_key": bool(os.getenv("GEMINI_API_KEY"))
    }


async def test_extraction(pdf_path: str) -> None:
    """Test function for the new extraction service."""
    print("Testing Gemini Extraction Service")
    print("=" * 50)
    
    # Check dependencies
    deps = check_dependencies()
    print("Dependencies:")
    for name, available in deps.items():
        print(f"  {name}: {'✓' if available else '✗'}")
    print()
    
    if not all(deps.values()):
        print("❌ Missing dependencies. Please install required packages and set GEMINI_API_KEY.")
        return
    
    # Run extraction
    service = GeminiExtractionService()
    result = await service.extract_fund(pdf_path)
    
    # Display results
    print(f"Extraction Result:")
    print(f"  Success: {result.success}")
    print(f"  Time: {result.extraction_time:.2f}s")
    
    if result.success:
        print(f"  Confidence: {result.confidence_score:.2f}")
        print(f"  Markdown length: {result.markdown_length:,} chars")
        print(f"  Tables extracted: {result.tables_extracted}")
        print(f"  Fund name: {result.fund_data.fund_name}")
        print(f"  Ticker: {result.fund_data.ticker}")
        print(f"  Fund type: {result.fund_data.fund_type}")
        print(f"  NAV: {result.fund_data.nav}")
        print(f"  Expense ratio: {result.fund_data.expense_ratio}")
        
        if result.warnings:
            print(f"  Warnings: {len(result.warnings)}")
            for warning in result.warnings:
                print(f"    - {warning}")
    else:
        print(f"  Error: {result.error}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        asyncio.run(test_extraction(pdf_path))
    else:
        print("Usage: python gemini_extraction_service.py <pdf_path>")
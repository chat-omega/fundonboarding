"""
Multi-fund extraction service using Docling for parsing and Gemini for extraction.
Handles documents containing multiple funds by splitting and extracting each fund separately.
"""

import asyncio
import json
import os
import re
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

# Fix environment variables BEFORE importing Docling
# Use appropriate HOME directory
if not os.path.exists('/app'):
    os.environ['HOME'] = os.path.expanduser('~')
else:
    os.environ['HOME'] = '/app'
os.environ['TMPDIR'] = '/tmp'
os.environ['XDG_CACHE_HOME'] = '/tmp/docling_cache'
os.environ['XDG_DATA_HOME'] = '/tmp/docling_data'

os.makedirs('/tmp/docling_cache', exist_ok=True)
os.makedirs('/tmp/docling_data', exist_ok=True)

try:
    from google import genai
    from google.genai.types import GenerateContentConfig
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    DocumentConverter = None

from pydantic import BaseModel

import sys
sys.path.append('..')
from src.models import FundData, FundComparisonData


@dataclass
class FundSection:
    """Represents a section of the document containing one fund."""
    fund_identifier: str
    section_title: str
    start_position: int
    end_position: int
    content: str
    page_numbers: List[int] = None


@dataclass
class MultiFundExtractionResult:
    """Result of multi-fund extraction."""
    success: bool
    funds_data: List[FundData] = None
    error: Optional[str] = None
    method_used: str = "gemini_multi_fund"
    extraction_time: float = 0.0
    total_funds_found: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    warnings: List[str] = None


class GeminiSplitter:
    """Splits multi-fund documents using Gemini AI."""
    
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
    
    def _create_splitting_prompt(self, markdown_content: str, document_filename: str) -> str:
        """Create prompt for fund splitting."""
        
        # Limit content for analysis (first ~500 lines for table of contents detection)
        lines = markdown_content.split('\n')
        limited_content = '\n'.join(lines[:min(500, len(lines))])
        
        prompt = f"""
You are a financial document analyzer. Analyze this multi-fund document to identify individual fund sections.

DOCUMENT: {document_filename}

DOCUMENT CONTENT:
{limited_content}

Your task is to identify all fund sections in this document. Look for:
- Fund names in titles, headers, or table of contents
- Asset Manager funds (e.g., "Asset Manager 20%", "Asset Manager 30%")  
- Section headers that indicate new funds
- Different investment objectives or strategies
- Separate fund identifiers or tickers

Return ONLY a valid JSON response with this structure:
{{
    "funds_found": [
        {{
            "fund_identifier": "unique_key_for_fund",
            "section_title": "Full section title as it appears",
            "fund_name": "Extracted fund name",
            "estimated_start_position": character_position_estimate,
            "section_markers": ["text patterns that indicate this section"]
        }}
    ],
    "total_funds": number_of_funds_found,
    "splitting_confidence": 0.0-1.0
}}

IMPORTANT RULES:
1. fund_identifier should be a clean key like "asset_manager_20", "asset_manager_30"
2. Look for consistent patterns (e.g., "Asset Manager X%" where X varies)
3. estimated_start_position is approximate character position where section begins
4. section_markers are text patterns that help locate the section
5. If no clear funds found, return empty funds_found array
6. Return ONLY the JSON object, no additional text

JSON:"""
        
        return prompt
    
    async def identify_fund_sections(self, markdown_content: str, document_filename: str) -> List[Dict[str, Any]]:
        """Identify fund sections using Gemini."""
        self._initialize()
        
        prompt = self._create_splitting_prompt(markdown_content, document_filename)
        
        config = GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=2048,
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
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result_dict = json.loads(json_str)
            else:
                result_dict = json.loads(response_text)
            
            return result_dict.get("funds_found", [])
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"Warning: Fund section identification failed: {e}")
            return []
    
    def split_document_by_sections(self, markdown_content: str, fund_sections: List[Dict[str, Any]]) -> List[FundSection]:
        """Split document content based on identified sections."""
        if not fund_sections:
            return []
        
        split_sections = []
        content_length = len(markdown_content)
        
        for i, section_info in enumerate(fund_sections):
            fund_id = section_info.get("fund_identifier", f"fund_{i+1}")
            section_title = section_info.get("section_title", f"Fund Section {i+1}")
            
            # Find actual start position using section markers
            start_pos = self._find_section_start(markdown_content, section_info)
            
            # Determine end position (start of next section or end of document)
            if i + 1 < len(fund_sections):
                end_pos = self._find_section_start(markdown_content, fund_sections[i + 1])
                if end_pos <= start_pos:
                    end_pos = content_length  # Fallback if next section not found
            else:
                end_pos = content_length
            
            # Extract section content
            section_content = markdown_content[start_pos:end_pos].strip()
            
            if section_content and len(section_content) > 100:  # Minimum content threshold
                split_sections.append(FundSection(
                    fund_identifier=fund_id,
                    section_title=section_title,
                    start_position=start_pos,
                    end_position=end_pos,
                    content=section_content
                ))
        
        return split_sections
    
    def _find_section_start(self, content: str, section_info: Dict[str, Any]) -> int:
        """Find the actual start position of a section using markers."""
        section_markers = section_info.get("section_markers", [])
        estimated_pos = section_info.get("estimated_start_position", 0)
        
        # Try to find section using markers
        for marker in section_markers:
            marker_pos = content.find(marker)
            if marker_pos != -1:
                return max(0, marker_pos)
        
        # Try to find using section title
        section_title = section_info.get("section_title", "")
        if section_title:
            title_pos = content.find(section_title)
            if title_pos != -1:
                return max(0, title_pos)
        
        # Fallback to estimated position
        return max(0, min(estimated_pos, len(content) - 1))


class GeminiMultiFundExtractor:
    """Multi-fund extractor using Docling + Gemini."""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.client = None
        self.docling_converter = None
        self.splitter = GeminiSplitter(api_key, model_name)
        self._initialized = False
    
    def _initialize(self):
        """Initialize services."""
        if self._initialized:
            return
        
        if not GEMINI_AVAILABLE:
            raise ImportError("Google GenAI not available. Install with: pip install google-genai")
        
        if not DOCLING_AVAILABLE:
            raise ImportError("Docling not available. Install with: pip install docling")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=self.api_key)
        self.docling_converter = DocumentConverter()
        self._initialized = True
    
    def _create_fund_extraction_prompt(self, section_content: str, fund_identifier: str, section_title: str) -> str:
        """Create extraction prompt for a single fund section."""
        
        prompt = f"""
You are a financial data extractor. Extract fund information from this section of a multi-fund document.

FUND SECTION: {section_title}
FUND IDENTIFIER: {fund_identifier}

SECTION CONTENT:
{section_content}

Extract the following information and return ONLY a valid JSON object:

{{
    "fund_name": "Full fund name as it appears",
    "ticker": "Ticker symbol if available or null",
    "fund_type": "Type of fund (ETF, Mutual Fund, Index Fund, etc.) or null",
    "target_equity_pct": "Target equity percentage if applicable (e.g. 20, 30, 40) or null",
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
    "expense_ratio": "Expense ratio as percentage (e.g. 0.48 for 0.48%) or null",
    "management_fee": "Management fee as percentage or null",
    
    // Performance
    "one_year_return": "One-year return as percentage or null",
    "portfolio_turnover": "Portfolio turnover rate as percentage or null",
    
    // Additional fields
    "number_of_holdings": "Total number of holdings as integer or null",
    "top_10_holdings": ["List of top 10 holdings with percentages"] or null,
    "sector_allocation": ["List of sector allocations with percentages"] or null,
    "fund_manager": "Fund manager or management team or null",
    "management_company": "Management company or fund family or null",
    "benchmark": "Primary benchmark index or null",
    "investment_objective": "Fund's investment objective or strategy description or null"
}}

EXTRACTION RULES:
1. Extract numeric values as numbers, not strings
2. Convert percentages to decimal format (e.g. "0.48%" becomes 0.48)
3. Use null for missing values, never empty strings
4. Focus on this specific fund section, ignore other funds
5. Look for financial highlights, portfolio composition, and holdings data
6. Extract fund name from section headers or fund-specific content
7. Return ONLY the JSON object, no additional text

JSON:"""
        
        return prompt
    
    async def extract_fund_from_section(self, section: FundSection) -> Optional[FundData]:
        """Extract fund data from a single section using Gemini."""
        self._initialize()
        
        prompt = self._create_fund_extraction_prompt(
            section.content, 
            section.fund_identifier, 
            section.section_title
        )
        
        config = GenerateContentConfig(
            temperature=0.1,
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
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                fund_dict = json.loads(json_str)
            else:
                fund_dict = json.loads(response_text)
            
            # Create FundData object
            fund_data = FundData(**fund_dict)
            
            # Add fallback fund name if missing
            if not fund_data.fund_name:
                fund_data.fund_name = section.section_title or section.fund_identifier
            
            return fund_data
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"Warning: Failed to extract fund data for {section.fund_identifier}: {e}")
            # Return minimal fund data as fallback
            return FundData(
                fund_name=section.section_title or section.fund_identifier,
                fund_type="Mutual Fund"
            )
    
    async def extract_multiple_funds(self, pdf_path: str) -> MultiFundExtractionResult:
        """Extract all funds from a multi-fund document."""
        start_time = time.time()
        warnings = []
        
        try:
            self._initialize()
            
            # Step 1: Parse document with Docling
            docling_result = self.docling_converter.convert(pdf_path)
            markdown_content = docling_result.document.export_to_markdown()
            
            if not markdown_content or len(markdown_content) < 500:
                return MultiFundExtractionResult(
                    success=False,
                    error="Document parsing produced insufficient content",
                    extraction_time=time.time() - start_time,
                    warnings=["Document too short or parsing failed"]
                )
            
            # Step 2: Identify fund sections
            document_filename = Path(pdf_path).name
            fund_sections_info = await self.splitter.identify_fund_sections(markdown_content, document_filename)
            
            if not fund_sections_info:
                return MultiFundExtractionResult(
                    success=False,
                    error="No fund sections identified in document",
                    extraction_time=time.time() - start_time,
                    warnings=["AI could not identify distinct fund sections"]
                )
            
            # Step 3: Split document into sections
            fund_sections = self.splitter.split_document_by_sections(markdown_content, fund_sections_info)
            
            if not fund_sections:
                return MultiFundExtractionResult(
                    success=False,
                    error="Document splitting failed",
                    extraction_time=time.time() - start_time,
                    warnings=["Could not split document into fund sections"]
                )
            
            print(f"Found {len(fund_sections)} fund sections")
            
            # Step 4: Extract data from each section in parallel
            extraction_tasks = [self.extract_fund_from_section(section) for section in fund_sections]
            fund_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
            
            # Step 5: Process results
            extracted_funds = []
            successful_extractions = 0
            failed_extractions = 0
            
            for i, result in enumerate(fund_results):
                if isinstance(result, Exception):
                    failed_extractions += 1
                    warnings.append(f"Failed to extract {fund_sections[i].fund_identifier}: {str(result)}")
                elif result:
                    extracted_funds.append(result)
                    successful_extractions += 1
                else:
                    failed_extractions += 1
                    warnings.append(f"No data extracted for {fund_sections[i].fund_identifier}")
            
            extraction_time = time.time() - start_time
            
            if not extracted_funds:
                return MultiFundExtractionResult(
                    success=False,
                    error="No funds successfully extracted",
                    extraction_time=extraction_time,
                    total_funds_found=len(fund_sections),
                    failed_extractions=failed_extractions,
                    warnings=warnings
                )
            
            return MultiFundExtractionResult(
                success=True,
                funds_data=extracted_funds,
                extraction_time=extraction_time,
                total_funds_found=len(fund_sections),
                successful_extractions=successful_extractions,
                failed_extractions=failed_extractions,
                warnings=warnings
            )
            
        except Exception as e:
            extraction_time = time.time() - start_time
            return MultiFundExtractionResult(
                success=False,
                error=f"Multi-fund extraction failed: {str(e)}",
                extraction_time=extraction_time,
                warnings=warnings
            )


# Global service instance
gemini_multi_fund_extractor = GeminiMultiFundExtractor()


def check_dependencies() -> Dict[str, bool]:
    """Check if required dependencies are available."""
    return {
        "docling": DOCLING_AVAILABLE,
        "google_genai": GEMINI_AVAILABLE,
        "gemini_api_key": bool(os.getenv("GEMINI_API_KEY"))
    }


async def test_multi_fund_extraction(pdf_path: str) -> None:
    """Test function for multi-fund extraction."""
    print("Testing Multi-Fund Extraction")
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
    extractor = GeminiMultiFundExtractor()
    result = await extractor.extract_multiple_funds(pdf_path)
    
    # Display results
    print(f"Multi-Fund Extraction Result:")
    print(f"  Success: {result.success}")
    print(f"  Time: {result.extraction_time:.2f}s")
    print(f"  Total funds found: {result.total_funds_found}")
    print(f"  Successful extractions: {result.successful_extractions}")
    print(f"  Failed extractions: {result.failed_extractions}")
    
    if result.success and result.funds_data:
        print(f"\nExtracted Funds:")
        for i, fund in enumerate(result.funds_data):
            print(f"  {i+1}. {fund.fund_name}")
            if fund.target_equity_pct:
                print(f"     Target Equity: {fund.target_equity_pct}%")
            if fund.nav:
                print(f"     NAV: ${fund.nav}")
            if fund.expense_ratio:
                print(f"     Expense Ratio: {fund.expense_ratio}%")
    
    if result.warnings:
        print(f"\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    if not result.success:
        print(f"\nError: {result.error}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        asyncio.run(test_multi_fund_extraction(pdf_path))
    else:
        print("Usage: python gemini_multi_fund_extractor.py <pdf_path>")
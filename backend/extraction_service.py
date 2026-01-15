"""
Enhanced Fund Extraction Service with AI-powered document classification and multi-fund support.
Integrates Docling + Gemini for both single and multi-fund extraction.
"""

import asyncio
import json
import os
import uuid
import time
from typing import Dict, List, Optional, Any, AsyncGenerator, Union
from pathlib import Path
from abc import ABC, abstractmethod
import pandas as pd
import re

import openai
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings
from llama_cloud_services import LlamaParse
from llama_cloud_services.extract import SourceText
from llama_cloud import ExtractConfig
from pydantic import BaseModel

import sys
sys.path.append('..')
from src.models import FundData
from config import config

# Import new AI-powered components
from document_classifier import DocumentClassifier, DocumentType, ClassificationResult
from gemini_multi_fund_extractor import GeminiMultiFundExtractor, MultiFundExtractionResult


class ExtractionResult(BaseModel):
    """Result of fund extraction (single or multi-fund)."""
    success: bool
    fund_data: Optional[Union[FundData, List[FundData]]] = None
    error: Optional[str] = None
    method_used: str
    extraction_time: float
    confidence_score: float = 0.0
    document_type: Optional[str] = None
    total_funds_extracted: int = 1
    classification_result: Optional[Dict] = None
    warnings: List[str] = None


class BaseExtractor(ABC):
    """Abstract base class for different extraction methods."""
    
    @abstractmethod
    async def extract(self, pdf_path: str) -> ExtractionResult:
        """Extract fund data from PDF."""
        pass
    
    @abstractmethod
    def can_handle(self, pdf_path: str) -> bool:
        """Check if this extractor can handle the given PDF."""
        pass


class LlamaParseExtractor(BaseExtractor):
    """Direct extraction using LlamaParse without splitting."""
    
    def __init__(self):
        self.parser = None
        self.llm = None
        self._initialized = False
    
    async def _initialize(self):
        """Initialize LlamaParse and LLM."""
        if self._initialized:
            return
        
        # Set up environment
        config.setup_environment()
        
        # Set up models
        embed_model = OpenAIEmbedding(model_name="text-embedding-3-small")
        self.llm = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        Settings.embed_model = embed_model
        
        # Set up parser
        self.parser = LlamaParse(
            premium_mode=True,
            result_type="markdown",
            project_id=os.getenv("PROJECT_ID"),
            organization_id=os.getenv("ORGANIZATION_ID"),
        )
        
        self._initialized = True
    
    def can_handle(self, pdf_path: str) -> bool:
        """Can handle any PDF."""
        return True
    
    async def extract(self, pdf_path: str) -> ExtractionResult:
        """Extract fund data using LlamaParse directly."""
        import time
        start_time = time.time()
        
        try:
            await self._initialize()
            
            # Parse PDF to markdown
            result = await self.parser.aparse(file_path=pdf_path)
            markdown_nodes = await result.aget_markdown_nodes()
            
            # Combine all content
            combined_text = "\n\n".join([n.get_content() for n in markdown_nodes])
            
            # Extract fund data using structured LLM
            fund_data = await self._extract_with_llm(combined_text, pdf_path)
            
            extraction_time = time.time() - start_time
            
            return ExtractionResult(
                success=True,
                fund_data=fund_data,
                method_used="llamaparse",
                extraction_time=extraction_time,
                confidence_score=0.8
            )
            
        except Exception as e:
            extraction_time = time.time() - start_time
            return ExtractionResult(
                success=False,
                error=str(e),
                method_used="llamaparse",
                extraction_time=extraction_time
            )
    
    async def _extract_with_llm(self, text: str, pdf_path: str) -> FundData:
        """Extract structured fund data using LLM."""
        
        # Get filename for ticker detection
        filename = Path(pdf_path).stem
        
        # Create extraction prompt
        prompt = f"""
Extract fund information from this ETF factsheet or fund document. 
The filename is: {filename}

Please extract the following information in JSON format:

{{
    "fund_name": "Full fund name (e.g. 'Vanguard Total Stock Market ETF')",
    "ticker": "Ticker symbol (e.g. 'VTI')",
    "fund_type": "Type of fund (e.g. 'ETF', 'Mutual Fund')",
    "expense_ratio": "Expense ratio as decimal (e.g. 0.03 for 0.03%)",
    "nav": "Net Asset Value or price per share",
    "net_assets_usd": "Total net assets in USD",
    "inception_date": "Fund inception date",
    "benchmark": "Benchmark index",
    "one_year_return": "1-year return as decimal",
    "equity_pct": "Equity allocation percentage",
    "fixed_income_pct": "Fixed income allocation percentage",
    "money_market_pct": "Money market allocation percentage"
}}

Document content:
{text[:8000]}  # Limit to first 8000 chars to avoid token limits
"""
        
        response = self.llm.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4096
        )
        
        try:
            # Try to parse JSON response
            json_match = re.search(r'\\{.*\\}', response.choices[0].message.content, re.DOTALL)
            if json_match:
                fund_dict = json.loads(json_match.group())
            else:
                # Fallback parsing
                fund_dict = self._parse_text_response(response.choices[0].message.content)
            
            # Add filename-based fallbacks
            if not fund_dict.get('ticker') and filename:
                fund_dict['ticker'] = filename.upper()
            
            if not fund_dict.get('fund_name'):
                ticker_to_name = {
                    "VTI": "Vanguard Total Stock Market ETF",
                    "VTV": "Vanguard Value ETF",
                    "VUG": "Vanguard Growth ETF",
                    "IVV": "iShares Core S&P 500 ETF",
                    "IEFA": "iShares Core MSCI EAFE ETF"
                }
                fund_dict['fund_name'] = ticker_to_name.get(filename.upper(), f"{filename.upper()} Fund")
            
            # Validate and create FundData
            fund_data = FundData(**fund_dict)
            return fund_data
            
        except Exception as e:
            # Create minimal fund data with filename fallback
            return FundData(
                fund_name=f"{filename.upper()} Fund",
                ticker=filename.upper() if filename else None,
                fund_type="ETF"
            )
    
    def _parse_text_response(self, text: str) -> Dict:
        """Parse text response when JSON parsing fails."""
        fund_dict = {}
        
        # Simple regex patterns to extract common fields
        patterns = {
            'fund_name': r'(?:fund[_ ]name|name)[:\s]+([^\\n]+)',
            'ticker': r'(?:ticker|symbol)[:\s]+([A-Z]{2,5})',
            'expense_ratio': r'(?:expense[_ ]ratio)[:\s]+([0-9.]+)',
            'nav': r'(?:nav|price)[:\s]+([0-9.,]+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if key in ['expense_ratio', 'nav'] and value:
                    try:
                        fund_dict[key] = float(value.replace(',', ''))
                    except:
                        pass
                else:
                    fund_dict[key] = value
        
        return fund_dict


class DirectLLMExtractor(BaseExtractor):
    """Extract using direct LLM without LlamaParse."""
    
    def __init__(self):
        self.llm = None
        self._initialized = False
    
    async def _initialize(self):
        if self._initialized:
            return
        
        # Set up environment
        config.setup_environment()
        
        self.llm = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._initialized = True
    
    def can_handle(self, pdf_path: str) -> bool:
        """Can handle any PDF."""
        return True
    
    async def extract(self, pdf_path: str) -> ExtractionResult:
        """Extract using PDF text extraction + LLM."""
        import time
        start_time = time.time()
        
        try:
            await self._initialize()
            
            # Simple PDF text extraction (can be improved)
            text = self._extract_text_from_pdf(pdf_path)
            
            # Extract with LLM
            fund_data = await self._extract_with_llm(text, pdf_path)
            
            extraction_time = time.time() - start_time
            
            return ExtractionResult(
                success=True,
                fund_data=fund_data,
                method_used="direct_llm",
                extraction_time=extraction_time,
                confidence_score=0.6
            )
            
        except Exception as e:
            extraction_time = time.time() - start_time
            return ExtractionResult(
                success=False,
                error=str(e),
                method_used="direct_llm",
                extraction_time=extraction_time
            )
    
    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Simple PDF text extraction."""
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
        except:
            # Fallback: return filename for basic extraction
            return f"Fund document: {Path(pdf_path).stem}"
    
    async def _extract_with_llm(self, text: str, pdf_path: str) -> FundData:
        """Extract structured data using LLM."""
        filename = Path(pdf_path).stem
        
        prompt = f"""
Extract fund data from this text. Filename: {filename}

Text: {text[:6000]}

Return only the fund name, ticker, and basic info you can find.
"""
        
        response = self.llm.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4096
        )
        
        # Create minimal fund data
        return FundData(
            fund_name=f"{filename.upper()} Fund",
            ticker=filename.upper() if filename else None,
            fund_type="ETF"
        )


class FundExtractionService:
    """Enhanced fund extraction service with AI-powered document classification."""
    
    def __init__(self):
        # Initialize legacy extractors (kept for backward compatibility)
        self.extractors = {
            'llamaparse': LlamaParseExtractor(),
            'direct_llm': DirectLLMExtractor(),
        }
        
        # Initialize AI-powered components
        self.document_classifier = None
        self.gemini_service = None
        self.multi_fund_extractor = None
        
        # Try to initialize new AI components
        self._initialize_ai_services()
        
        self.default_method = 'auto'  # Changed from 'llamaparse' to 'auto'
    
    def _initialize_ai_services(self):
        """Initialize AI-powered extraction services."""
        try:
            # Initialize document classifier
            self.document_classifier = DocumentClassifier()
            
            # Initialize single-fund Gemini service
            from gemini_extraction_service import GeminiExtractionService
            self.gemini_service = GeminiExtractionService()
            
            # Initialize multi-fund extractor
            self.multi_fund_extractor = GeminiMultiFundExtractor()
            
            print("✓ AI-powered extraction services initialized")
            
        except ImportError as e:
            print(f"Warning: Could not import AI services: {e}")
            self.document_classifier = None
            self.gemini_service = None
            self.multi_fund_extractor = None
    
    async def classify_document(self, pdf_path: str) -> ClassificationResult:
        """Classify document using AI analysis."""
        if self.document_classifier:
            return await self.document_classifier.classify_document(pdf_path)
        else:
            # Fallback to filename-based classification
            return self._fallback_classification(pdf_path)
    
    def _fallback_classification(self, pdf_path: str) -> ClassificationResult:
        """Fallback classification based on filename patterns."""
        filename = Path(pdf_path).name.upper()
        
        # Single fund patterns
        single_patterns = [
            r'^V[A-Z]{2,3}\.PDF$',
            r'^I[A-Z]{2,4}\.PDF$',
            r'.*ETF.*FACT.*SHEET.*\.PDF$',
        ]
        
        # Multi fund patterns  
        multi_patterns = [
            r'.*ASSET.MANAGER.*\.PDF$',
            r'.*ANNUAL.REPORT.*\.PDF$',
            r'.*CONSOLIDATED.*\.PDF$',
        ]
        
        for pattern in single_patterns:
            if re.match(pattern, filename):
                return ClassificationResult(
                    document_type=DocumentType.SINGLE_FUND,
                    confidence=0.7,
                    reasoning="Filename pattern suggests single fund ETF"
                )
        
        for pattern in multi_patterns:
            if re.match(pattern, filename):
                return ClassificationResult(
                    document_type=DocumentType.MULTI_FUND,
                    confidence=0.7,
                    reasoning="Filename pattern suggests multi-fund document"
                )
        
        return ClassificationResult(
            document_type=DocumentType.SINGLE_FUND,  # Safe default
            confidence=0.5,
            reasoning="Unknown pattern, defaulting to single fund"
        )
    
    def should_use_ai_extraction(self) -> bool:
        """Determine if AI extraction should be used."""
        return (
            config.extraction_method in ["auto", "gemini"] and
            config.gemini_api_key and
            self.gemini_service and 
            self.multi_fund_extractor and
            self.document_classifier
        )
    
    async def extract_fund(self, pdf_path: str, method: str = 'auto') -> ExtractionResult:
        """Extract fund data from PDF with intelligent routing."""
        start_time = time.time()
        warnings = []
        
        try:
            # Step 1: Determine extraction approach
            if method == 'auto':
                if self.should_use_ai_extraction():
                    method = 'ai_powered'
                elif self.gemini_service:
                    method = 'gemini'
                else:
                    method = 'llamaparse'
            
            # Step 2: AI-powered extraction (new approach)
            if method == 'ai_powered':
                return await self._extract_with_ai_routing(pdf_path, start_time)
            
            # Step 3: Legacy Gemini extraction (single fund only)
            elif method == 'gemini' and self.gemini_service:
                try:
                    gemini_result = await self.gemini_service.extract_fund(pdf_path)
                    return ExtractionResult(
                        success=gemini_result.success,
                        fund_data=gemini_result.fund_data,
                        error=gemini_result.error,
                        method_used=gemini_result.method_used,
                        extraction_time=gemini_result.extraction_time,
                        confidence_score=gemini_result.confidence_score,
                        document_type="single_fund",
                        warnings=gemini_result.warnings
                    )
                except Exception as e:
                    return ExtractionResult(
                        success=False,
                        error=f"Gemini extraction error: {str(e)}",
                        method_used="gemini",
                        extraction_time=time.time() - start_time
                    )
            
            # Step 4: Legacy extraction methods
            else:
                extractor = self.extractors.get(method)
                if not extractor:
                    return ExtractionResult(
                        success=False,
                        error=f"Unknown extraction method: {method}",
                        method_used=method,
                        extraction_time=time.time() - start_time
                    )
                
                legacy_result = await extractor.extract(pdf_path)
                # Convert to new format
                return ExtractionResult(
                    success=legacy_result.success,
                    fund_data=legacy_result.fund_data,
                    error=legacy_result.error,
                    method_used=legacy_result.method_used,
                    extraction_time=legacy_result.extraction_time,
                    confidence_score=legacy_result.confidence_score,
                    document_type="single_fund"
                )
        
        except Exception as e:
            return ExtractionResult(
                success=False,
                error=f"Extraction failed: {str(e)}",
                method_used=method,
                extraction_time=time.time() - start_time
            )
    
    async def _extract_with_ai_routing(self, pdf_path: str, start_time: float) -> ExtractionResult:
        """Extract using AI-powered document classification and routing."""
        
        # Step 1: Classify document
        classification = await self.classify_document(pdf_path)
        
        classification_dict = {
            "document_type": classification.document_type.value,
            "confidence": classification.confidence,
            "reasoning": classification.reasoning,
            "fund_count_estimate": classification.fund_count_estimate,
            "fund_names": classification.fund_names
        }
        
        # Step 2: Route based on classification
        if classification.document_type == DocumentType.SINGLE_FUND:
            # Single fund extraction
            try:
                gemini_result = await self.gemini_service.extract_fund(pdf_path)
                return ExtractionResult(
                    success=gemini_result.success,
                    fund_data=gemini_result.fund_data,
                    error=gemini_result.error,
                    method_used="ai_powered_single",
                    extraction_time=time.time() - start_time,
                    confidence_score=gemini_result.confidence_score,
                    document_type=classification.document_type.value,
                    classification_result=classification_dict,
                    warnings=gemini_result.warnings or []
                )
            except Exception as e:
                return ExtractionResult(
                    success=False,
                    error=f"Single fund extraction failed: {str(e)}",
                    method_used="ai_powered_single",
                    extraction_time=time.time() - start_time,
                    document_type=classification.document_type.value,
                    classification_result=classification_dict
                )
        
        elif classification.document_type == DocumentType.MULTI_FUND:
            # Multi-fund extraction
            try:
                multi_result = await self.multi_fund_extractor.extract_multiple_funds(pdf_path)
                
                if multi_result.success:
                    return ExtractionResult(
                        success=True,
                        fund_data=multi_result.funds_data,
                        method_used="ai_powered_multi",
                        extraction_time=time.time() - start_time,
                        confidence_score=0.8,  # Multi-fund extractions are generally high confidence
                        document_type=classification.document_type.value,
                        total_funds_extracted=len(multi_result.funds_data) if multi_result.funds_data else 0,
                        classification_result=classification_dict,
                        warnings=multi_result.warnings or []
                    )
                else:
                    return ExtractionResult(
                        success=False,
                        error=f"Multi-fund extraction failed: {multi_result.error}",
                        method_used="ai_powered_multi",
                        extraction_time=time.time() - start_time,
                        document_type=classification.document_type.value,
                        classification_result=classification_dict,
                        warnings=multi_result.warnings or []
                    )
                    
            except Exception as e:
                return ExtractionResult(
                    success=False,
                    error=f"Multi-fund extraction error: {str(e)}",
                    method_used="ai_powered_multi", 
                    extraction_time=time.time() - start_time,
                    document_type=classification.document_type.value,
                    classification_result=classification_dict
                )
        
        else:
            # Unknown document type - fallback to single fund
            return ExtractionResult(
                success=False,
                error="Document type classification failed",
                method_used="ai_powered_unknown",
                extraction_time=time.time() - start_time,
                document_type=classification.document_type.value,
                classification_result=classification_dict
            )
    
    async def extract_multiple_documents(self, pdf_paths: List[str], method: str = 'auto') -> List[ExtractionResult]:
        """Extract multiple documents in parallel."""
        tasks = [self.extract_fund(path, method) for path in pdf_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(ExtractionResult(
                    success=False,
                    error=str(result),
                    method_used=method,
                    extraction_time=0.0
                ))
            else:
                final_results.append(result)
        
        return final_results


# Global service instance
extraction_service = FundExtractionService()
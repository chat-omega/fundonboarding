"""Extraction Agent that integrates our existing Fidelity extraction engine."""

import asyncio
import time
from typing import AsyncGenerator, Dict, List, Optional
from pathlib import Path

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent, AgentType, AgentMessage, MessageType
from models.unified_models import (
    PortfolioItem, DocumentSource, ExtendedFundData, ExtractionResult, extend_fund_data
)
# Temporarily disable tracing imports
from utils.llamaindex_callbacks import setup_llamaindex_callbacks

# Import our existing extraction components
import sys
sys.path.append('..')
sys.path.append('../..')
from config import config
from src.fund_extractor import FidelityFundExtraction, setup_extract_agent, aextract_data_over_splits
from src.split_detector import afind_categories_and_splits
from src.models import FundData
from llama_cloud_services import LlamaParse
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings


class ExtractionAgent(BaseAgent):
    """Agent responsible for extracting fund data from documents using our proven extraction engine."""
    
    def __init__(self, session_id: str):
        super().__init__(AgentType.EXTRACTION, session_id)
        self.fidelity_extractor = None
        self.llamaparse = None
        self.llm = None
        self.extract_agent = None
        
    async def _setup(self) -> None:
        """Initialize extraction components."""
        try:
            # Validate configuration
            if not config.validate():
                raise Exception("Invalid configuration. Please check API keys.")
            
            # Set up environment
            config.setup_environment()
            
            # Initialize AI models
            self.llm = OpenAI(
                model="gpt-4o-mini",
                temperature=0.1,
                max_tokens=4000,
                logprobs=False,
                default_headers={}
            )
            
            embedding_model = OpenAIEmbedding(
                model="text-embedding-3-small",
                dimensions=1536,
            )
            
            # Set global settings
            Settings.llm = self.llm
            Settings.embed_model = embedding_model
            
            # Set up LangSmith callbacks for LlamaIndex
            setup_llamaindex_callbacks()
            
            # Initialize LlamaParse
            self.llamaparse = LlamaParse(
                result_type="text",
                verbose=True,
                language="en",
                num_workers=1
            )
            
            # Initialize extraction agent
            self.extract_agent = setup_extract_agent()
            
            # Note: Fidelity extractor will be created lazily when needed
            self.fidelity_extractor = None
            
            self.set_confidence_score("extraction_setup", 0.9)
            
        except Exception as e:
            print(f"Error setting up extraction agent: {e}")
            self.set_confidence_score("extraction_setup", 0.0)
            raise
            
    async def _cleanup(self) -> None:
        """Cleanup extraction resources."""
        # Cleanup is handled by the underlying components
        pass
        
    async def process(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Process documents and extract fund data."""
        
        if (message.type == MessageType.DATA_PROCESSED and 
            "document_sources" in message.data and 
            "portfolio_items" in message.data):
            
            document_sources = [DocumentSource(**doc) for doc in message.data["document_sources"]]
            portfolio_items = [PortfolioItem(**item) for item in message.data["portfolio_items"]]
            
            yield await self.emit_status("starting_extraction", {
                "total_documents": len(document_sources),
                "stage": "document_processing"
            })
            
            extraction_results = []
            processed_count = 0
            
            # Process each document
            for doc_source in document_sources:
                try:
                    ticker = doc_source.ticker
                    
                    yield await self.emit_status("extracting_fund", {
                        "ticker": ticker,
                        "document_path": doc_source.local_path,
                        "progress": processed_count / len(document_sources)
                    })
                    
                    # Extract fund data from document
                    extraction_result = await self._extract_from_document(doc_source)
                    
                    if extraction_result:
                        extraction_results.append(extraction_result)
                        
                        # Emit individual extraction result
                        yield self.create_message(
                            message_type=MessageType.STATUS_UPDATE,
                            recipient=None,
                            data={
                                "type": "fund_extracted",
                                "ticker": ticker,
                                "fund_name": extraction_result.extracted_data.fund_name,
                                "confidence": extraction_result.confidence_score,
                                "processing_time": extraction_result.processing_time
                            }
                        )
                    else:
                        yield self.create_message(
                            message_type=MessageType.STATUS_UPDATE,
                            recipient=None,
                            data={
                                "type": "extraction_failed",
                                "ticker": ticker,
                                "message": f"Failed to extract data from {ticker} document"
                            }
                        )
                    
                    processed_count += 1
                    
                except Exception as e:
                    yield await self.emit_error(f"Failed to extract {doc_source.ticker}: {str(e)}", {
                        "ticker": doc_source.ticker,
                        "document_path": doc_source.local_path,
                        "error_type": type(e).__name__
                    })
                    processed_count += 1
            
            # Emit final results to next agent
            yield self.create_message(
                message_type=MessageType.DATA_PROCESSED,
                recipient=AgentType.CATEGORIZATION,
                data={
                    "portfolio_items": message.data["portfolio_items"],
                    "extraction_results": [result.model_dump() for result in extraction_results],
                    "extraction_summary": {
                        "total_processed": len(document_sources),
                        "successful_extractions": len(extraction_results),
                        "success_rate": len(extraction_results) / len(document_sources) if document_sources else 0
                    }
                }
            )
    
    async def _extract_from_document(self, doc_source: DocumentSource) -> Optional[ExtractionResult]:
        """Extract fund data from a single document."""
        if not doc_source.local_path or not Path(doc_source.local_path).exists():
            return None
            
        start_time = time.time()
        
        try:
            # Try using the unified extraction service first
            try:
                from ..extraction_service import extraction_service
                
                # Use the unified extraction service which handles method selection
                unified_result = await extraction_service.extract_fund(doc_source.local_path)
                
                if unified_result.success and unified_result.fund_data:
                    # Create extended fund data
                    extended_fund_data = extend_fund_data(
                        original=unified_result.fund_data,
                        ticker=doc_source.ticker,
                        data_source="pdf",
                        extraction_method=unified_result.method_used,
                        source_document=doc_source.local_path,
                        confidence_score=unified_result.confidence_score,
                        processing_time=unified_result.extraction_time
                    )
                    
                    # Calculate field confidence
                    field_confidence = self._calculate_field_confidence(unified_result.fund_data)
                    
                    # Create extraction result
                    extraction_result = ExtractionResult(
                        source=doc_source,
                        extracted_data=extended_fund_data,
                        processing_time=unified_result.extraction_time,
                        extraction_method=unified_result.method_used,
                        confidence_score=unified_result.confidence_score,
                        field_confidence=field_confidence,
                        warnings=[],
                        errors=[],
                        requires_review=unified_result.confidence_score < 0.7
                    )
                    
                    return extraction_result
                    
            except ImportError:
                # Fall back to legacy extraction if unified service not available
                pass
            
            # Fallback to legacy extraction methods
            extraction_method = self._determine_extraction_method(doc_source.local_path)
            
            if extraction_method == "fidelity":
                fund_data = await self._extract_fidelity_format(doc_source.local_path)
            elif extraction_method == "vanguard":
                fund_data = await self._extract_vanguard_format(doc_source.local_path)
            else:
                fund_data = await self._extract_generic_format(doc_source.local_path)
            
            if not fund_data:
                return None
            
            processing_time = time.time() - start_time
            
            # Create extended fund data
            extended_fund_data = extend_fund_data(
                original=fund_data,
                ticker=doc_source.ticker,
                data_source="pdf",
                extraction_method=extraction_method,
                source_document=doc_source.local_path,
                confidence_score=self._calculate_extraction_confidence(fund_data),
                processing_time=processing_time
            )
            
            # Calculate confidence scores
            confidence_score = self._calculate_extraction_confidence(fund_data)
            field_confidence = self._calculate_field_confidence(fund_data)
            
            # Create extraction result
            extraction_result = ExtractionResult(
                source=doc_source,
                extracted_data=extended_fund_data,
                processing_time=processing_time,
                extraction_method=extraction_method,
                confidence_score=confidence_score,
                field_confidence=field_confidence,
                warnings=[],
                errors=[],
                requires_review=confidence_score < 0.7
            )
            
            return extraction_result
            
        except Exception as e:
            print(f"Extraction error for {doc_source.ticker}: {e}")
            return None
    
    def _determine_extraction_method(self, file_path: str) -> str:
        """Determine the best extraction method based on document analysis."""
        try:
            # Quick analysis of document content to determine format
            with open(file_path, 'rb') as f:
                # Read first few KB to analyze
                content = f.read(8192).decode('utf-8', errors='ignore').lower()
                
                if 'fidelity' in content and 'asset manager' in content:
                    return "fidelity"
                elif 'vanguard' in content:
                    return "vanguard"
                else:
                    return "generic"
                    
        except:
            return "generic"
    
    async def _extract_fidelity_format(self, file_path: str) -> Optional[FundData]:
        """Extract data using our proven Fidelity extraction method."""
        try:
            # Parse the PDF
            documents = await self.llamaparse.aload_data(file_path)
            
            if not documents:
                return None
            
            # Use our existing splitting logic
            splits = await afind_categories_and_splits(documents)
            
            if not splits:
                return None
            
            # Extract data using our existing extraction method
            # Create nodes from the splits for the function call
            nodes = splits.get("documents", [])
            split_name_to_pages = {k: v.get("pages", []) for k, v in splits.items() if k != "documents"}
            fund_data_list = await aextract_data_over_splits(split_name_to_pages, nodes, self.extract_agent, llm=self.llm)
            
            if fund_data_list:
                # Return first fund (could be enhanced to handle multiple)
                return fund_data_list[0]
                
            return None
            
        except Exception as e:
            print(f"Fidelity extraction error: {e}")
            return None
    
    async def _extract_vanguard_format(self, file_path: str) -> Optional[FundData]:
        """Extract data from Vanguard format documents."""
        try:
            # Parse the PDF
            documents = await self.llamaparse.aload_data(file_path)
            
            if not documents:
                return None
            
            # For Vanguard, we'll adapt our extraction approach
            # Create a single "split" representing the entire document
            splits = {
                "Vanguard Fund": {
                    "pages": list(range(len(documents))),
                    "documents": documents
                }
            }
            
            # Use our extraction agent with Vanguard-specific context
            # Create nodes from the splits for the function call
            nodes = splits.get("documents", [])
            split_name_to_pages = {k: v.get("pages", []) for k, v in splits.items() if k != "documents"}
            fund_data_list = await aextract_data_over_splits(split_name_to_pages, nodes, self.extract_agent, llm=self.llm)
            
            if fund_data_list:
                return fund_data_list[0]
                
            return None
            
        except Exception as e:
            print(f"Vanguard extraction error: {e}")
            return None
    
    async def _extract_generic_format(self, file_path: str) -> Optional[FundData]:
        """Extract data from generic fund documents."""
        try:
            # Parse the PDF
            documents = await self.llamaparse.aload_data(file_path)
            
            if not documents:
                return None
            
            # Create a generic split
            splits = {
                "Generic Fund": {
                    "pages": list(range(len(documents))),
                    "documents": documents
                }
            }
            
            # Use our extraction agent
            # Create nodes from the splits for the function call
            nodes = splits.get("documents", [])
            split_name_to_pages = {k: v.get("pages", []) for k, v in splits.items() if k != "documents"}
            fund_data_list = await aextract_data_over_splits(split_name_to_pages, nodes, self.extract_agent, llm=self.llm)
            
            if fund_data_list:
                return fund_data_list[0]
                
            return None
            
        except Exception as e:
            print(f"Generic extraction error: {e}")
            return None
    
    def _calculate_extraction_confidence(self, fund_data: FundData) -> float:
        """Calculate confidence score for extraction results."""
        if not fund_data:
            return 0.0
            
        # Score based on data completeness
        fields = fund_data.model_dump()
        total_fields = len(fields)
        filled_fields = sum(1 for value in fields.values() if value is not None)
        
        completeness_score = filled_fields / total_fields
        
        # Bonus for key fields
        key_fields = ['fund_name', 'nav', 'expense_ratio', 'one_year_return']
        key_score = sum(1 for field in key_fields if getattr(fund_data, field, None) is not None)
        key_bonus = key_score / len(key_fields) * 0.2
        
        return min(1.0, completeness_score * 0.8 + key_bonus)
    
    def _calculate_field_confidence(self, fund_data: FundData) -> Dict[str, float]:
        """Calculate confidence scores for individual fields."""
        field_confidence = {}
        fields = fund_data.model_dump()
        
        for field_name, value in fields.items():
            if value is None:
                field_confidence[field_name] = 0.0
            elif isinstance(value, str):
                # String fields: confidence based on length and content
                if len(value.strip()) > 0:
                    field_confidence[field_name] = 0.9
                else:
                    field_confidence[field_name] = 0.0
            elif isinstance(value, (int, float)):
                # Numeric fields: high confidence if reasonable values
                if field_name.endswith('_pct') and 0 <= value <= 100:
                    field_confidence[field_name] = 0.95
                elif field_name == 'expense_ratio' and 0 <= value <= 5:
                    field_confidence[field_name] = 0.95
                elif value > 0:
                    field_confidence[field_name] = 0.9
                else:
                    field_confidence[field_name] = 0.5
            else:
                field_confidence[field_name] = 0.8
                
        return field_confidence
    
    async def generate_extraction_summary(self, results: List[ExtractionResult]) -> str:
        """Generate a summary of extraction results."""
        if not results:
            return "❌ No fund data was successfully extracted. Please check the document format and try again."
        
        total_extractions = len(results)
        high_confidence = sum(1 for r in results if r.confidence_score >= 0.8)
        medium_confidence = sum(1 for r in results if 0.5 <= r.confidence_score < 0.8)
        low_confidence = sum(1 for r in results if r.confidence_score < 0.5)
        
        summary_parts = [
            f"✅ Successfully extracted data from **{total_extractions} fund documents**!"
        ]
        
        if high_confidence > 0:
            summary_parts.append(f"🎯 {high_confidence} extractions with high confidence (≥80%)")
            
        if medium_confidence > 0:
            summary_parts.append(f"⚠️ {medium_confidence} extractions with medium confidence (50-80%)")
            
        if low_confidence > 0:
            summary_parts.append(f"🔍 {low_confidence} extractions with low confidence (<50%) - may need review")
        
        # List extracted funds
        fund_names = []
        for result in results[:5]:  # Show first 5
            name = result.extracted_data.fund_name or result.source.ticker
            confidence = int(result.confidence_score * 100)
            fund_names.append(f"{name} ({confidence}%)")
        
        if fund_names:
            summary_parts.append(f"**Extracted funds:** {', '.join(fund_names)}")
            if len(results) > 5:
                summary_parts.append(f"and {len(results) - 5} more...")
        
        summary_parts.append("Ready for analysis and categorization! 📊")
        
        return " ".join(summary_parts)


class DocumentAnalyzer:
    """Helper class to analyze document structure and content."""
    
    @staticmethod
    def analyze_document_type(file_path: str) -> Dict[str, any]:
        """Analyze document to determine type and characteristics."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read(16384).decode('utf-8', errors='ignore').lower()
            
            analysis = {
                "is_fidelity": "fidelity" in content,
                "is_vanguard": "vanguard" in content,
                "is_prospectus": "prospectus" in content,
                "has_fund_data": any(term in content for term in ["nav", "expense ratio", "return"]),
                "language": "en",  # Could be enhanced with language detection
                "estimated_pages": content.count('\f') + 1  # Page breaks
            }
            
            return analysis
            
        except Exception as e:
            return {"error": str(e), "is_valid": False}
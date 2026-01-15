"""Research Agent for finding and downloading fund documents."""

import asyncio
import aiohttp
import re
import os
from typing import AsyncGenerator, Dict, List, Optional, Tuple
from pathlib import Path
from urllib.parse import urljoin, urlparse
import hashlib

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent, AgentType, AgentMessage, MessageType
from models.unified_models import PortfolioItem, DocumentSource
# Temporarily disable tracing imports


class ResearchAgent(BaseAgent):
    """Agent responsible for finding and downloading fund prospectuses."""
    
    def __init__(self, session_id: str):
        super().__init__(AgentType.RESEARCH, session_id)
        # Use Docker path if available, fallback to local dev path
        self.cache_dir = Path("/app/data/downloads") if Path("/app/data/downloads").parent.exists() else Path("../../data/downloads")
        self.download_timeout = 30  # seconds
        self.max_file_size = 50 * 1024 * 1024  # 50MB max
        
        # Fund provider URL patterns
        self.provider_patterns = {
            "vanguard": {
                "base_url": "https://advisors.vanguard.com",
                "search_url": "https://advisors.vanguard.com/investments/products/{ticker}",
                "prospectus_patterns": [
                    r'href="([^"]*prospectus[^"]*\.pdf)"',
                    r'href="([^"]*summary[^"]*\.pdf)"'
                ]
            },
            "sec": {
                "base_url": "https://www.sec.gov",
                "search_url": "https://www.sec.gov/edgar/search/?r=el#/dateRange=custom&entityName={ticker}&startdt=2023-01-01&enddt=2024-12-31",
                "prospectus_patterns": [
                    r'href="([^"]*\.pdf)"'
                ]
            },
            "morningstar": {
                "base_url": "https://www.morningstar.com",
                "search_url": "https://www.morningstar.com/etfs/{ticker}",
                "prospectus_patterns": [
                    r'href="([^"]*prospectus[^"]*\.pdf)"'
                ]
            }
        }
        
    async def _setup(self) -> None:
        """Initialize the research agent."""
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.set_confidence_score("document_search", 0.8)
        
    async def _cleanup(self) -> None:
        """Cleanup resources."""
        pass
        
    async def process(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """Process portfolio items and find fund documents."""
        
        if message.type == MessageType.DATA_PROCESSED and "portfolio_items" in message.data:
            portfolio_data = message.data["portfolio_items"]
            
            yield await self.emit_status("starting_research", {
                "total_funds": len(portfolio_data),
                "stage": "document_discovery"
            })
            
            documents_found = []
            processed_count = 0
            
            # Process each portfolio item
            for item_data in portfolio_data:
                try:
                    portfolio_item = PortfolioItem(**item_data)
                    ticker = portfolio_item.ticker.upper()
                    
                    yield await self.emit_status("researching_fund", {
                        "ticker": ticker,
                        "fund_name": portfolio_item.name,
                        "progress": processed_count / len(portfolio_data)
                    })
                    
                    # Search for documents
                    document_source = await self._find_fund_document(portfolio_item)
                    
                    if document_source:
                        documents_found.append(document_source)
                        
                        yield self.create_message(
                            message_type=MessageType.STATUS_UPDATE,
                            recipient=None,
                            data={
                                "type": "document_found",
                                "ticker": ticker,
                                "source": document_source.model_dump(),
                                "confidence": document_source.confidence
                            }
                        )
                    else:
                        yield self.create_message(
                            message_type=MessageType.STATUS_UPDATE,
                            recipient=None,
                            data={
                                "type": "document_not_found",
                                "ticker": ticker,
                                "message": f"Could not find prospectus for {ticker}"
                            }
                        )
                    
                    processed_count += 1
                    
                except Exception as e:
                    yield await self.emit_error(f"Failed to research {portfolio_item.ticker}: {str(e)}", {
                        "ticker": portfolio_item.ticker,
                        "error_type": type(e).__name__
                    })
                    processed_count += 1
            
            # Emit results to next agent
            yield self.create_message(
                message_type=MessageType.DATA_PROCESSED,
                recipient=AgentType.EXTRACTION,
                data={
                    "portfolio_items": portfolio_data,
                    "document_sources": [doc.model_dump() for doc in documents_found],
                    "research_summary": {
                        "total_researched": len(portfolio_data),
                        "documents_found": len(documents_found),
                        "success_rate": len(documents_found) / len(portfolio_data) if portfolio_data else 0
                    }
                }
            )
    
    async def _find_fund_document(self, portfolio_item: PortfolioItem) -> Optional[DocumentSource]:
        """Find fund document for a specific portfolio item."""
        ticker = portfolio_item.ticker.upper()
        
        # Check if we already have the document locally
        local_source = await self._check_local_cache(ticker)
        if local_source:
            return local_source
        
        # Try different providers in order of preference
        providers = ["vanguard", "sec", "morningstar"]  # Vanguard first for ETFs
        
        for provider in providers:
            try:
                document_source = await self._search_provider(ticker, provider, portfolio_item.name)
                if document_source:
                    return document_source
                    
            except Exception as e:
                print(f"Error searching {provider} for {ticker}: {e}")
                continue
        
        return None
    
    async def _check_local_cache(self, ticker: str) -> Optional[DocumentSource]:
        """Check if document exists in local cache."""
        # Check for exact ticker match
        potential_files = [
            f"{ticker}.pdf",
            f"{ticker.lower()}.pdf",
            f"{ticker}_prospectus.pdf"
        ]
        
        for filename in potential_files:
            file_path = self.cache_dir / filename
            if file_path.exists():
                return DocumentSource(
                    local_path=str(file_path),
                    document_type="prospectus",
                    ticker=ticker,
                    file_size=file_path.stat().st_size,
                    confidence=0.95,  # High confidence for local files
                    source_rating="verified"
                )
        
        return None
    
    async def _search_provider(self, ticker: str, provider: str, fund_name: str) -> Optional[DocumentSource]:
        """Search a specific provider for fund documents."""
        if provider not in self.provider_patterns:
            return None
            
        provider_config = self.provider_patterns[provider]
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.download_timeout)) as session:
                # Format search URL
                search_url = provider_config["search_url"].format(ticker=ticker.lower())
                
                # Get the page content
                async with session.get(search_url) as response:
                    if response.status != 200:
                        return None
                        
                    content = await response.text()
                    
                    # Search for prospectus links
                    prospectus_url = self._extract_prospectus_url(
                        content, 
                        provider_config["prospectus_patterns"],
                        provider_config["base_url"]
                    )
                    
                    if prospectus_url:
                        # Download the document
                        local_path = await self._download_document(session, prospectus_url, ticker)
                        
                        if local_path:
                            return DocumentSource(
                                url=prospectus_url,
                                local_path=local_path,
                                document_type="prospectus",
                                ticker=ticker,
                                confidence=0.8,
                                source_rating="official" if provider == "sec" else "verified"
                            )
        
        except Exception as e:
            print(f"Error searching {provider} for {ticker}: {e}")
            return None
            
        return None
    
    def _extract_prospectus_url(self, content: str, patterns: List[str], base_url: str) -> Optional[str]:
        """Extract prospectus URL from page content."""
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Clean up the URL
                if match.startswith('http'):
                    return match
                elif match.startswith('/'):
                    return urljoin(base_url, match)
                else:
                    return urljoin(base_url, '/' + match)
        
        return None
    
    async def _download_document(self, session: aiohttp.ClientSession, url: str, ticker: str) -> Optional[str]:
        """Download document from URL to local cache."""
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                
                # Check file size
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > self.max_file_size:
                    print(f"File too large for {ticker}: {content_length} bytes")
                    return None
                
                # Generate local filename
                local_filename = f"{ticker}_prospectus.pdf"
                local_path = self.cache_dir / local_filename
                
                # Download the file
                content = await response.read()
                
                # Validate it's a PDF
                if not content.startswith(b'%PDF'):
                    print(f"Downloaded file for {ticker} is not a valid PDF")
                    return None
                
                # Save to local cache
                with open(local_path, 'wb') as f:
                    f.write(content)
                
                print(f"Downloaded {ticker} prospectus: {local_path}")
                return str(local_path)
                
        except Exception as e:
            print(f"Error downloading document for {ticker}: {e}")
            return None
    
    def _calculate_search_confidence(self, ticker: str, found_documents: List[DocumentSource]) -> float:
        """Calculate confidence in document search results."""
        if not found_documents:
            return 0.0
        
        # Base confidence on source quality and document type
        total_confidence = 0.0
        for doc in found_documents:
            doc_confidence = doc.confidence
            
            # Boost confidence for official sources
            if doc.source_rating == "official":
                doc_confidence *= 1.2
            elif doc.source_rating == "verified":
                doc_confidence *= 1.1
                
            # Boost for prospectus documents
            if "prospectus" in doc.document_type.lower():
                doc_confidence *= 1.1
                
            total_confidence += min(1.0, doc_confidence)
        
        return min(1.0, total_confidence / len(found_documents))
    
    async def generate_research_summary(self, portfolio_items: List[PortfolioItem], documents: List[DocumentSource]) -> str:
        """Generate a summary of research results."""
        total_funds = len(portfolio_items)
        found_docs = len(documents)
        success_rate = (found_docs / total_funds * 100) if total_funds > 0 else 0
        
        summary_parts = [
            f"📊 Research completed! I found prospectuses for **{found_docs} out of {total_funds}** funds ({success_rate:.0f}% success rate)."
        ]
        
        if found_docs > 0:
            # Group by source type
            local_docs = sum(1 for doc in documents if doc.local_path and not doc.url)
            downloaded_docs = sum(1 for doc in documents if doc.url)
            
            if local_docs > 0:
                summary_parts.append(f"📁 {local_docs} documents were already available locally.")
            if downloaded_docs > 0:
                summary_parts.append(f"🔍 {downloaded_docs} documents were downloaded from official sources.")
            
            # List found tickers
            found_tickers = [doc.ticker for doc in documents]
            summary_parts.append(f"Found documents for: {', '.join(found_tickers)}")
            
        if found_docs < total_funds:
            missing_count = total_funds - found_docs
            summary_parts.append(f"⚠️ Could not find prospectuses for {missing_count} funds. I'll proceed with available data.")
        
        summary_parts.append("Shall I now extract detailed fund information from these documents?")
        
        return " ".join(summary_parts)


class DocumentValidator:
    """Helper class to validate downloaded documents."""
    
    @staticmethod
    def is_valid_pdf(file_path: str) -> bool:
        """Check if file is a valid PDF."""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                return header == b'%PDF'
        except:
            return False
    
    @staticmethod
    def get_file_hash(file_path: str) -> str:
        """Generate hash for file integrity checking."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    @staticmethod
    def is_fund_document(content: str, ticker: str) -> bool:
        """Check if document content is related to the fund."""
        # Simple heuristics to check document relevance
        ticker_found = ticker.upper() in content.upper()
        fund_keywords = any(keyword in content.lower() for keyword in [
            'prospectus', 'fund', 'etf', 'investment', 'portfolio'
        ])
        return ticker_found and fund_keywords


class WebScraper:
    """Helper class for web scraping fund information."""
    
    @staticmethod
    def extract_fund_links(html_content: str, base_url: str) -> List[str]:
        """Extract potential fund document links from HTML."""
        patterns = [
            r'href="([^"]*prospectus[^"]*\.pdf)"',
            r'href="([^"]*annual[^"]*report[^"]*\.pdf)"',
            r'href="([^"]*summary[^"]*\.pdf)"',
            r'href="([^"]*fact[^"]*sheet[^"]*\.pdf)"'
        ]
        
        links = []
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match.startswith('http'):
                    links.append(match)
                else:
                    links.append(urljoin(base_url, match))
        
        return list(set(links))  # Remove duplicates
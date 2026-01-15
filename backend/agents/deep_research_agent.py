"""Deep Research Agent for fund analysis using LangChain Open Deep Research patterns."""

import asyncio
import aiohttp
import json
import logging
from typing import AsyncGenerator, Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from urllib.parse import quote_plus
import hashlib

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent, AgentType, AgentMessage, MessageType
from models.unified_models import PortfolioItem
# Temporarily disable tracing imports

logger = logging.getLogger(__name__)


@dataclass
class ResearchQuery:
    """Individual research query for a fund."""
    fund_ticker: str
    query_text: str
    query_type: str  # "basic", "holdings", "performance", "category"
    priority: int = 1  # 1=high, 2=medium, 3=low


@dataclass
class ResearchResult:
    """Result from a research query."""
    fund_ticker: str
    query_type: str
    source_url: str
    content: str
    confidence: float
    extracted_data: Dict[str, Any]
    timestamp: datetime


class DeepResearchAgent(BaseAgent):
    """
    Deep Research Agent implementing LangChain Open Deep Research patterns.
    
    Three-phase process:
    1. Scoping: Generate research queries for each fund
    2. Research: Execute parallel web searches and data extraction  
    3. Synthesis: Analyze results and prepare for classification
    """
    
    def __init__(self, session_id: str):
        super().__init__(AgentType.RESEARCH, session_id)
        self.search_timeout = 10  # seconds per search
        self.max_parallel_searches = 5
        self.cache_duration = timedelta(hours=24)  # Cache results for 24 hours
        
        # Research sources and patterns
        self.search_sources = {
            "tavily": {
                "enabled": bool(os.getenv("TAVILY_API_KEY")),
                "api_key": os.getenv("TAVILY_API_KEY"),
                "base_url": "https://api.tavily.com/search"
            },
            "serper": {
                "enabled": bool(os.getenv("SERPER_API_KEY")),
                "api_key": os.getenv("SERPER_API_KEY"),
                "base_url": "https://google.serper.dev/search"
            },
            "duckduckgo": {
                "enabled": True,  # Free fallback
                "base_url": "https://api.duckduckgo.com"
            }
        }
        
        # Fund data extraction patterns
        self.extraction_patterns = {
            "morningstar_category": [
                r"Morningstar Category[:\s]+([^,\n]+)",
                r"Category[:\s]+([A-Z][^,\n]+Fund[^,\n]*)",
                r"Fund Category[:\s]+([^,\n]+)"
            ],
            "expense_ratio": [
                r"Expense Ratio[:\s]+([\d.]+)%?",
                r"Management Fee[:\s]+([\d.]+)%?",
                r"Annual Fee[:\s]+([\d.]+)%?"
            ],
            "asset_class": [
                r"Asset Class[:\s]+([^,\n]+)",
                r"Investment Type[:\s]+([^,\n]+)",
                r"Fund Type[:\s]+([^,\n]+)"
            ],
            "holdings": [
                r"Top (\d+) Holdings?[:\s]*(.{0,500})",
                r"Largest Holdings?[:\s]*(.{0,500})",
                r"Major Holdings?[:\s]*(.{0,500})"
            ]
        }
        
        # Cache for research results
        self.research_cache: Dict[str, ResearchResult] = {}
        
    async def _setup(self) -> None:
        """Initialize the deep research agent."""
        logger.info(f"🔬 Setting up DeepResearchAgent for session: {self.session_id}")
        
        # Validate available search APIs
        available_sources = []
        for source, config in self.search_sources.items():
            if config["enabled"]:
                available_sources.append(source)
        
        if not available_sources:
            logger.warning("⚠️ No search APIs configured - using fallback methods")
        else:
            logger.info(f"🔬 Available search sources: {available_sources}")
        
        self.set_confidence_score("research_setup", 0.9)
        
    async def _cleanup(self) -> None:
        """Cleanup resources."""
        # Clear cache if needed
        self.research_cache.clear()
        
    async def process(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """
        Process portfolio items with deep research.
        
        Implements three-phase Open Deep Research pattern:
        1. Scoping: Generate targeted research queries
        2. Research: Execute parallel searches with sub-agents
        3. Synthesis: Compile results for classification
        """
        
        if message.type == MessageType.DATA_PROCESSED and "portfolio_items" in message.data:
            portfolio_data = message.data["portfolio_items"]
            
            yield await self.emit_status("starting_deep_research", {
                "total_funds": len(portfolio_data),
                "stage": "scoping",
                "message": "Planning research strategy..."
            })
            
            # Phase 1: Scoping - Generate research queries
            research_plan = await self._generate_research_plan(portfolio_data)
            
            yield await self.emit_status("research_planned", {
                "total_queries": len(research_plan),
                "stage": "research",
                "message": f"Generated {len(research_plan)} research queries"
            })
            
            # Phase 2: Research - Execute parallel searches
            research_results = await self._execute_research_plan(research_plan)
            
            # Update progress as we get results
            for i, result in enumerate(research_results):
                yield self.create_message(
                    message_type=MessageType.STATUS_UPDATE,
                    recipient=None,
                    data={
                        "type": "research_result",
                        "ticker": result.fund_ticker,
                        "query_type": result.query_type,
                        "confidence": result.confidence,
                        "progress": (i + 1) / len(research_results)
                    }
                )
            
            yield await self.emit_status("research_complete", {
                "total_results": len(research_results),
                "stage": "synthesis",
                "message": "Analyzing research findings..."
            })
            
            # Phase 3: Synthesis - Prepare for classification
            synthesized_data = await self._synthesize_research_results(
                portfolio_data, research_results
            )
            
            # Emit enhanced portfolio data with research
            yield self.create_message(
                message_type=MessageType.DATA_PROCESSED,
                recipient=AgentType.CHAT_ORCHESTRATOR,  # Send to classification stage
                data={
                    "portfolio_items": portfolio_data,
                    "research_results": [r.__dict__ for r in research_results],
                    "synthesized_data": synthesized_data,
                    "research_summary": {
                        "total_funds_researched": len(portfolio_data),
                        "successful_queries": len([r for r in research_results if r.confidence > 0.5]),
                        "research_quality": sum(r.confidence for r in research_results) / len(research_results) if research_results else 0.0
                    }
                }
            )
    
    async def _generate_research_plan(self, portfolio_items: List[Dict]) -> List[ResearchQuery]:
        """
        Generate targeted research queries for each fund.
        
        Creates multiple query types for comprehensive fund analysis.
        """
        queries = []
        
        for item_data in portfolio_items:
            portfolio_item = PortfolioItem(**item_data)
            ticker = portfolio_item.ticker.upper()
            fund_name = portfolio_item.name
            
            # Basic fund information query
            queries.append(ResearchQuery(
                fund_ticker=ticker,
                query_text=f"{ticker} {fund_name} fund factsheet prospectus expense ratio",
                query_type="basic",
                priority=1
            ))
            
            # Holdings and composition query
            queries.append(ResearchQuery(
                fund_ticker=ticker,
                query_text=f"{ticker} fund top holdings asset allocation composition",
                query_type="holdings",
                priority=1
            ))
            
            # Category and classification query
            queries.append(ResearchQuery(
                fund_ticker=ticker,
                query_text=f"{ticker} Morningstar category asset class investment type",
                query_type="category",
                priority=1
            ))
            
            # Performance and risk query
            queries.append(ResearchQuery(
                fund_ticker=ticker,
                query_text=f"{ticker} fund performance returns risk profile volatility",
                query_type="performance",
                priority=2
            ))
            
        # Sort by priority for efficient processing
        queries.sort(key=lambda q: q.priority)
        
        logger.info(f"🔬 Generated {len(queries)} research queries for {len(portfolio_items)} funds")
        return queries
    
    async def _execute_research_plan(self, research_plan: List[ResearchQuery]) -> List[ResearchResult]:
        """
        Execute research queries in parallel using sub-agent pattern.
        
        Implements parallel processing with rate limiting and fallbacks.
        """
        results = []
        
        # Process in batches to avoid overwhelming APIs
        batch_size = self.max_parallel_searches
        batches = [research_plan[i:i + batch_size] for i in range(0, len(research_plan), batch_size)]
        
        for batch_idx, batch in enumerate(batches):
            logger.info(f"🔬 Processing research batch {batch_idx + 1}/{len(batches)} ({len(batch)} queries)")
            
            # Create tasks for parallel execution
            tasks = [self._execute_single_query(query) for query in batch]
            
            # Execute batch with timeout protection
            try:
                batch_results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.search_timeout * 2
                )
                
                # Filter successful results
                for result in batch_results:
                    if isinstance(result, ResearchResult):
                        results.append(result)
                    elif isinstance(result, Exception):
                        logger.warning(f"🔬 Research query failed: {str(result)}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"🔬 Batch {batch_idx + 1} timed out")
                continue
            
            # Small delay between batches to be respectful to APIs
            if batch_idx < len(batches) - 1:
                await asyncio.sleep(1)
        
        logger.info(f"🔬 Completed research: {len(results)} successful results")
        return results
    
    async def _execute_single_query(self, query: ResearchQuery) -> Optional[ResearchResult]:
        """Execute a single research query with fallback sources."""
        
        # Check cache first
        cache_key = f"{query.fund_ticker}:{query.query_type}:{hashlib.md5(query.query_text.encode()).hexdigest()[:8]}"
        if cache_key in self.research_cache:
            cached_result = self.research_cache[cache_key]
            if datetime.now() - cached_result.timestamp < self.cache_duration:
                return cached_result
        
        # Try each available search source
        for source_name, config in self.search_sources.items():
            if not config["enabled"]:
                continue
                
            try:
                result = await self._search_with_source(source_name, query)
                if result and result.confidence > 0.3:  # Minimum quality threshold
                    # Cache the result
                    self.research_cache[cache_key] = result
                    return result
                    
            except Exception as e:
                logger.warning(f"🔬 Search failed with {source_name}: {str(e)}")
                continue
        
        # If all sources fail, create a minimal result
        return ResearchResult(
            fund_ticker=query.fund_ticker,
            query_type=query.query_type,
            source_url="fallback",
            content="",
            confidence=0.1,
            extracted_data={},
            timestamp=datetime.now()
        )
    
    async def _search_with_source(self, source_name: str, query: ResearchQuery) -> Optional[ResearchResult]:
        """Execute search with a specific source."""
        
        if source_name == "tavily" and self.search_sources["tavily"]["enabled"]:
            return await self._search_tavily(query)
        elif source_name == "serper" and self.search_sources["serper"]["enabled"]:
            return await self._search_serper(query)
        elif source_name == "duckduckgo":
            return await self._search_duckduckgo(query)
        
        return None
    
    async def _search_tavily(self, query: ResearchQuery) -> Optional[ResearchResult]:
        """Search using Tavily API."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "api_key": self.search_sources["tavily"]["api_key"],
                    "query": query.query_text,
                    "search_depth": "basic",
                    "include_answer": True,
                    "include_raw_content": False,
                    "max_results": 5
                }
                
                async with session.post(
                    self.search_sources["tavily"]["base_url"],
                    json=payload,
                    timeout=self.search_timeout
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._extract_from_tavily_response(query, data)
                        
        except Exception as e:
            logger.warning(f"🔬 Tavily search failed: {str(e)}")
            
        return None
    
    async def _search_serper(self, query: ResearchQuery) -> Optional[ResearchResult]:
        """Search using Serper API."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "X-API-KEY": self.search_sources["serper"]["api_key"],
                    "Content-Type": "application/json"
                }
                payload = {
                    "q": query.query_text,
                    "num": 5
                }
                
                async with session.post(
                    self.search_sources["serper"]["base_url"],
                    json=payload,
                    headers=headers,
                    timeout=self.search_timeout
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._extract_from_serper_response(query, data)
                        
        except Exception as e:
            logger.warning(f"🔬 Serper search failed: {str(e)}")
            
        return None
    
    async def _search_duckduckgo(self, query: ResearchQuery) -> Optional[ResearchResult]:
        """Search using DuckDuckGo (free fallback)."""
        try:
            # Simple web search simulation for fallback
            # In production, you might use a proper DuckDuckGo API wrapper
            search_url = f"https://duckduckgo.com/?q={quote_plus(query.query_text)}"
            
            return ResearchResult(
                fund_ticker=query.fund_ticker,
                query_type=query.query_type,
                source_url=search_url,
                content=f"Search query: {query.query_text}",
                confidence=0.3,  # Lower confidence for fallback
                extracted_data={"search_url": search_url},
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.warning(f"🔬 DuckDuckGo search failed: {str(e)}")
            
        return None
    
    def _extract_from_tavily_response(self, query: ResearchQuery, response_data: Dict) -> ResearchResult:
        """Extract fund data from Tavily search results."""
        
        combined_content = ""
        extracted_data = {}
        best_url = ""
        
        # Combine results from multiple sources
        if "results" in response_data:
            for result in response_data["results"][:3]:  # Top 3 results
                content = result.get("content", "")
                combined_content += content + "\n\n"
                
                if not best_url and "url" in result:
                    best_url = result["url"]
        
        # Use answer if available
        if "answer" in response_data:
            combined_content = response_data["answer"] + "\n\n" + combined_content
        
        # Extract structured data using patterns
        extracted_data = self._extract_fund_data(combined_content, query.query_type)
        
        # Calculate confidence based on extracted data quality
        confidence = self._calculate_extraction_confidence(extracted_data, query.query_type)
        
        return ResearchResult(
            fund_ticker=query.fund_ticker,
            query_type=query.query_type,
            source_url=best_url or "tavily",
            content=combined_content[:2000],  # Limit content size
            confidence=confidence,
            extracted_data=extracted_data,
            timestamp=datetime.now()
        )
    
    def _extract_from_serper_response(self, query: ResearchQuery, response_data: Dict) -> ResearchResult:
        """Extract fund data from Serper search results."""
        
        combined_content = ""
        extracted_data = {}
        best_url = ""
        
        # Process organic results
        if "organic" in response_data:
            for result in response_data["organic"][:3]:
                snippet = result.get("snippet", "")
                combined_content += snippet + "\n\n"
                
                if not best_url and "link" in result:
                    best_url = result["link"]
        
        # Check for answer box or knowledge graph
        if "answerBox" in response_data:
            answer = response_data["answerBox"].get("answer", "")
            combined_content = answer + "\n\n" + combined_content
        
        # Extract structured data
        extracted_data = self._extract_fund_data(combined_content, query.query_type)
        confidence = self._calculate_extraction_confidence(extracted_data, query.query_type)
        
        return ResearchResult(
            fund_ticker=query.fund_ticker,
            query_type=query.query_type,
            source_url=best_url or "serper",
            content=combined_content[:2000],
            confidence=confidence,
            extracted_data=extracted_data,
            timestamp=datetime.now()
        )
    
    def _extract_fund_data(self, content: str, query_type: str) -> Dict[str, Any]:
        """Extract structured fund data from text content using patterns."""
        
        extracted = {}
        
        # Apply extraction patterns based on query type
        if query_type in ["basic", "category"]:
            # Extract Morningstar category
            for pattern in self.extraction_patterns["morningstar_category"]:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    extracted["morningstar_category"] = match.group(1).strip()
                    break
            
            # Extract expense ratio
            for pattern in self.extraction_patterns["expense_ratio"]:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    try:
                        extracted["expense_ratio"] = float(match.group(1))
                    except ValueError:
                        pass
                    break
            
            # Extract asset class
            for pattern in self.extraction_patterns["asset_class"]:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    extracted["asset_class"] = match.group(1).strip()
                    break
        
        if query_type == "holdings":
            # Extract holdings information
            for pattern in self.extraction_patterns["holdings"]:
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    holdings_text = match.group(2) if len(match.groups()) > 1 else match.group(1)
                    extracted["holdings_text"] = holdings_text.strip()
                    break
        
        # Add metadata
        extracted["content_length"] = len(content)
        extracted["extraction_timestamp"] = datetime.now().isoformat()
        
        return extracted
    
    def _calculate_extraction_confidence(self, extracted_data: Dict[str, Any], query_type: str) -> float:
        """Calculate confidence score based on extracted data quality."""
        
        confidence = 0.1  # Base confidence
        
        # Boost confidence based on found data
        if "morningstar_category" in extracted_data:
            confidence += 0.3
        if "expense_ratio" in extracted_data:
            confidence += 0.2  
        if "asset_class" in extracted_data:
            confidence += 0.25
        if "holdings_text" in extracted_data:
            confidence += 0.15
        
        # Content quality indicators
        content_length = extracted_data.get("content_length", 0)
        if content_length > 100:
            confidence += 0.1
        if content_length > 500:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    async def _synthesize_research_results(
        self, 
        portfolio_items: List[Dict], 
        research_results: List[ResearchResult]
    ) -> Dict[str, Any]:
        """
        Synthesize research results into actionable fund intelligence.
        
        Combines multiple research results per fund into coherent profiles.
        """
        
        synthesized = {}
        
        # Group results by fund ticker
        results_by_fund = {}
        for result in research_results:
            ticker = result.fund_ticker
            if ticker not in results_by_fund:
                results_by_fund[ticker] = []
            results_by_fund[ticker].append(result)
        
        # Create synthesized profile for each fund
        for ticker, fund_results in results_by_fund.items():
            fund_profile = {
                "ticker": ticker,
                "research_sources": len(fund_results),
                "overall_confidence": sum(r.confidence for r in fund_results) / len(fund_results),
                "data_points": {},
                "suggested_categories": {},
                "research_summary": ""
            }
            
            # Merge extracted data with conflict resolution
            all_extracted = {}
            for result in fund_results:
                for key, value in result.extracted_data.items():
                    if key not in all_extracted:
                        all_extracted[key] = []
                    all_extracted[key].append((value, result.confidence))
            
            # Select best value for each data point
            for key, value_confidence_pairs in all_extracted.items():
                # Sort by confidence and take the best
                best_value, best_confidence = max(value_confidence_pairs, key=lambda x: x[1])
                fund_profile["data_points"][key] = {
                    "value": best_value,
                    "confidence": best_confidence,
                    "alternatives": [v for v, c in value_confidence_pairs if v != best_value]
                }
            
            # Generate category suggestions based on research
            fund_profile["suggested_categories"] = self._generate_category_suggestions(fund_profile)
            
            synthesized[ticker] = fund_profile
        
        logger.info(f"🔬 Synthesized research for {len(synthesized)} funds")
        return synthesized
    
    def _generate_category_suggestions(self, fund_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate category suggestions based on research data."""
        
        suggestions = {
            "asset_class": {"suggestion": "Unknown", "confidence": 0.1, "reasoning": "Insufficient data"},
            "equity_style": None,
            "equity_size": None,
            "fixed_income_type": None
        }
        
        data_points = fund_profile.get("data_points", {})
        
        # Analyze Morningstar category if available
        if "morningstar_category" in data_points:
            category = data_points["morningstar_category"]["value"].lower()
            confidence = data_points["morningstar_category"]["confidence"]
            
            # Map Morningstar categories to asset classes
            if any(keyword in category for keyword in ["equity", "stock", "large", "mid", "small"]):
                suggestions["asset_class"] = {
                    "suggestion": "Equity",
                    "confidence": confidence,
                    "reasoning": f"Morningstar category: {category}"
                }
                
                # Determine equity style
                if "value" in category:
                    suggestions["equity_style"] = {"suggestion": "Value", "confidence": confidence * 0.8}
                elif "growth" in category:
                    suggestions["equity_style"] = {"suggestion": "Growth", "confidence": confidence * 0.8}
                elif "blend" in category or "core" in category:
                    suggestions["equity_style"] = {"suggestion": "Blend", "confidence": confidence * 0.8}
                
                # Determine equity size
                if "large" in category:
                    suggestions["equity_size"] = {"suggestion": "Large", "confidence": confidence * 0.8}
                elif "mid" in category:
                    suggestions["equity_size"] = {"suggestion": "Mid", "confidence": confidence * 0.8}
                elif "small" in category:
                    suggestions["equity_size"] = {"suggestion": "Small", "confidence": confidence * 0.8}
                    
            elif any(keyword in category for keyword in ["bond", "fixed", "income", "treasury", "corporate"]):
                suggestions["asset_class"] = {
                    "suggestion": "Fixed Income",
                    "confidence": confidence,
                    "reasoning": f"Morningstar category: {category}"
                }
                
                # Determine fixed income type
                if "government" in category or "treasury" in category:
                    suggestions["fixed_income_type"] = {"suggestion": "Government", "confidence": confidence * 0.8}
                elif "corporate" in category:
                    suggestions["fixed_income_type"] = {"suggestion": "Corporate", "confidence": confidence * 0.8}
                elif "high yield" in category or "junk" in category:
                    suggestions["fixed_income_type"] = {"suggestion": "High Yield", "confidence": confidence * 0.8}
        
        # Analyze asset class field if available
        if "asset_class" in data_points:
            asset_class = data_points["asset_class"]["value"].lower()
            confidence = data_points["asset_class"]["confidence"]
            
            if any(keyword in asset_class for keyword in ["equity", "stock"]):
                suggestions["asset_class"] = {
                    "suggestion": "Equity",
                    "confidence": confidence,
                    "reasoning": f"Explicit asset class: {asset_class}"
                }
            elif any(keyword in asset_class for keyword in ["bond", "fixed", "income"]):
                suggestions["asset_class"] = {
                    "suggestion": "Fixed Income", 
                    "confidence": confidence,
                    "reasoning": f"Explicit asset class: {asset_class}"
                }
        
        return suggestions
"""Classification Agent for intelligent fund categorization using ML models."""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, List, Optional, Any, Tuple, Literal
from dataclasses import dataclass, field
from datetime import datetime
import re
import numpy as np
from collections import defaultdict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent, AgentType, AgentMessage, MessageType
from models.unified_models import PortfolioItem
# Temporarily disable tracing imports

logger = logging.getLogger(__name__)


@dataclass 
class ClassificationRule:
    """Rule for fund classification."""
    pattern: str
    asset_class: str
    sub_categories: Dict[str, str]
    confidence: float
    priority: int


@dataclass
class ClassificationResult:
    """Result of fund classification."""
    ticker: str
    fund_name: str
    
    # Primary classification
    asset_class: Literal["Equity", "Fixed Income", "Cash", "Alternatives"]
    asset_class_confidence: float
    
    # Equity sub-categories
    equity_region: Optional[Literal["US", "International", "Emerging", "Global"]] = None
    equity_style: Optional[Literal["Value", "Growth", "Blend"]] = None  
    equity_size: Optional[Literal["Large", "Mid", "Small", "Micro"]] = None
    
    # Fixed Income sub-categories
    fixed_income_type: Optional[Literal["Government", "Corporate", "Municipal", "High Yield"]] = None
    fixed_income_duration: Optional[Literal["Short", "Intermediate", "Long"]] = None
    
    # Research metadata
    research_sources: List[str] = field(default_factory=list)
    key_data_points: Dict[str, Any] = field(default_factory=dict)
    morningstar_category: Optional[str] = None
    
    # Classification metadata
    classification_method: str = "unknown"
    reasoning: str = ""
    alternative_classifications: List[Dict[str, Any]] = field(default_factory=list)
    
    # Override capability
    manual_override: bool = False
    override_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "ticker": self.ticker,
            "fund_name": self.fund_name,
            "asset_class": self.asset_class,
            "confidence": self.asset_class_confidence,
            "sub_categories": {},
            "research_sources": self.research_sources,
            "key_data_points": self.key_data_points,
            "morningstar_category": self.morningstar_category,
            "classification_method": self.classification_method,
            "reasoning": self.reasoning,
            "alternatives": self.alternative_classifications,
            "manual_override": self.manual_override,
            "override_reason": self.override_reason
        }
        
        # Add sub-categories
        if self.equity_region:
            result["sub_categories"]["equity_region"] = self.equity_region
        if self.equity_style:
            result["sub_categories"]["equity_style"] = self.equity_style
        if self.equity_size:
            result["sub_categories"]["equity_size"] = self.equity_size
        if self.fixed_income_type:
            result["sub_categories"]["fixed_income_type"] = self.fixed_income_type
        if self.fixed_income_duration:
            result["sub_categories"]["fixed_income_duration"] = self.fixed_income_duration
            
        return result


class ClassificationAgent(BaseAgent):
    """
    Agent responsible for intelligent fund categorization.
    
    Uses multiple approaches:
    1. Rule-based classification using known patterns
    2. ML-based classification using fund characteristics
    3. Research-based classification using external data
    4. Confidence scoring and alternative suggestions
    """
    
    def __init__(self, session_id: str):
        super().__init__(AgentType.CHAT_ORCHESTRATOR, session_id)  # Temporary - will create proper type
        
        # Classification rules database
        self.classification_rules = self._build_classification_rules()
        
        # Known fund mappings for high-confidence classification
        self.known_funds = self._build_known_funds_database()
        
        # Pattern matching weights
        self.classification_weights = {
            "ticker_pattern": 0.3,
            "name_pattern": 0.25,
            "morningstar_category": 0.4,
            "research_data": 0.35,
            "known_fund": 0.9
        }
        
    async def _setup(self) -> None:
        """Initialize the classification agent."""
        logger.info(f"🏷️ Setting up ClassificationAgent for session: {self.session_id}")
        
        # Validate rule database
        logger.info(f"🏷️ Loaded {len(self.classification_rules)} classification rules")
        logger.info(f"🏷️ Loaded {len(self.known_funds)} known fund mappings")
        
        self.set_confidence_score("classification_ready", 0.95)
        
    async def _cleanup(self) -> None:
        """Cleanup resources."""
        pass
        
    async def process(self, message: AgentMessage) -> AsyncGenerator[AgentMessage, None]:
        """
        Process research results and classify funds.
        
        Takes research data and produces classification results with confidence scores.
        """
        
        if (message.type == MessageType.DATA_PROCESSED and 
            "synthesized_data" in message.data and 
            "portfolio_items" in message.data):
            
            portfolio_data = message.data["portfolio_items"]
            research_data = message.data.get("synthesized_data", {})
            
            yield await self.emit_status("starting_classification", {
                "total_funds": len(portfolio_data),
                "stage": "analysis",
                "message": "Analyzing fund characteristics..."
            })
            
            classifications = []
            
            for i, item_data in enumerate(portfolio_data):
                portfolio_item = PortfolioItem(**item_data)
                ticker = portfolio_item.ticker.upper()
                
                yield await self.emit_status("classifying_fund", {
                    "ticker": ticker,
                    "fund_name": portfolio_item.name,
                    "progress": i / len(portfolio_data),
                    "stage": "classification"
                })
                
                # Get research data for this fund
                fund_research = research_data.get(ticker, {})
                
                # Perform classification
                classification = await self._classify_fund(portfolio_item, fund_research)
                classifications.append(classification)
                
                # Emit individual classification result
                yield self.create_message(
                    message_type=MessageType.STATUS_UPDATE,
                    recipient=None,
                    data={
                        "type": "fund_classified",
                        "ticker": ticker,
                        "asset_class": classification.asset_class,
                        "confidence": classification.asset_class_confidence,
                        "sub_categories": len([x for x in [
                            classification.equity_region,
                            classification.equity_style,
                            classification.equity_size,
                            classification.fixed_income_type,
                            classification.fixed_income_duration
                        ] if x is not None]),
                        "method": classification.classification_method
                    }
                )
            
            # Calculate overall classification quality
            avg_confidence = sum(c.asset_class_confidence for c in classifications) / len(classifications)
            high_confidence_count = len([c for c in classifications if c.asset_class_confidence >= 0.8])
            
            yield await self.emit_status("classification_complete", {
                "total_classified": len(classifications),
                "average_confidence": avg_confidence,
                "high_confidence_count": high_confidence_count,
                "stage": "complete"
            })
            
            # Prepare categorization data for chat interface
            categorization_data = {
                "classifications": [c.to_dict() for c in classifications],
                "summary": {
                    "total_funds": len(classifications),
                    "average_confidence": avg_confidence,
                    "high_confidence_percentage": high_confidence_count / len(classifications) * 100,
                    "asset_class_breakdown": self._calculate_asset_class_breakdown(classifications),
                    "requires_user_input": len([c for c in classifications if c.asset_class_confidence < 0.7])
                },
                "interaction_needed": self._determine_interaction_needs(classifications)
            }
            
            # Send to chat orchestrator for user interaction
            yield self.create_message(
                message_type=MessageType.DATA_PROCESSED,
                recipient=AgentType.CHAT_ORCHESTRATOR,
                data={
                    "type": "categorization_results",
                    "portfolio_items": portfolio_data,
                    "categorization_data": categorization_data,
                    "next_action": "user_review" if categorization_data["summary"]["requires_user_input"] > 0 else "finalize"
                }
            )
    
    async def _classify_fund(self, portfolio_item: PortfolioItem, research_data: Dict[str, Any]) -> ClassificationResult:
        """
        Classify a single fund using multiple approaches.
        
        Combines rule-based, pattern-based, and research-based classification.
        """
        ticker = portfolio_item.ticker.upper()
        fund_name = portfolio_item.name
        
        # Initialize result
        classification = ClassificationResult(
            ticker=ticker,
            fund_name=fund_name,
            asset_class="Equity",  # Default, will be updated
            asset_class_confidence=0.1,
            research_sources=[],
            key_data_points={},
            classification_method="unknown",
            reasoning="No classification method succeeded",
            alternative_classifications=[]
        )
        
        # Collection of all classification attempts
        classification_attempts = []
        
        # Method 1: Check known funds database
        known_result = self._classify_known_fund(ticker, fund_name)
        if known_result:
            classification_attempts.append({
                "method": "known_fund",
                "confidence": 0.95,
                "result": known_result
            })
        
        # Method 2: Rule-based classification using patterns
        rule_result = self._classify_by_rules(ticker, fund_name, portfolio_item.asset_class)
        if rule_result:
            classification_attempts.append({
                "method": "rule_based",
                "confidence": rule_result.get("confidence", 0.7),
                "result": rule_result
            })
        
        # Method 3: Research-based classification
        if research_data and "suggested_categories" in research_data:
            research_result = self._classify_by_research(research_data)
            if research_result:
                classification_attempts.append({
                    "method": "research_based", 
                    "confidence": research_result.get("confidence", 0.6),
                    "result": research_result
                })
        
        # Method 4: Morningstar category mapping
        morningstar_category = None
        if research_data and "data_points" in research_data:
            data_points = research_data["data_points"]
            if "morningstar_category" in data_points:
                morningstar_category = data_points["morningstar_category"]["value"]
                morningstar_result = self._classify_by_morningstar(morningstar_category)
                if morningstar_result:
                    classification_attempts.append({
                        "method": "morningstar",
                        "confidence": data_points["morningstar_category"]["confidence"],
                        "result": morningstar_result
                    })
        
        # Select best classification attempt
        if classification_attempts:
            # Sort by confidence and select best
            best_attempt = max(classification_attempts, key=lambda x: x["confidence"])
            
            # Apply best classification
            result_data = best_attempt["result"]
            classification.asset_class = result_data["asset_class"]
            classification.asset_class_confidence = best_attempt["confidence"]
            classification.classification_method = best_attempt["method"]
            classification.reasoning = result_data.get("reasoning", "")
            
            # Apply sub-categories
            if "equity_region" in result_data:
                classification.equity_region = result_data["equity_region"]
            if "equity_style" in result_data:
                classification.equity_style = result_data["equity_style"]
            if "equity_size" in result_data:
                classification.equity_size = result_data["equity_size"]
            if "fixed_income_type" in result_data:
                classification.fixed_income_type = result_data["fixed_income_type"]
            if "fixed_income_duration" in result_data:
                classification.fixed_income_duration = result_data["fixed_income_duration"]
            
            # Store alternatives (other classification attempts)
            classification.alternative_classifications = [
                {
                    "method": attempt["method"],
                    "confidence": attempt["confidence"],
                    "asset_class": attempt["result"]["asset_class"],
                    "reasoning": attempt["result"].get("reasoning", "")
                }
                for attempt in classification_attempts if attempt != best_attempt
            ]
        
        # Add research metadata
        classification.morningstar_category = morningstar_category
        if research_data:
            classification.research_sources = [
                source for source in research_data.get("research_sources", [])
            ]
            classification.key_data_points = research_data.get("data_points", {})
        
        return classification
    
    def _classify_known_fund(self, ticker: str, fund_name: str) -> Optional[Dict[str, Any]]:
        """Classify using known funds database."""
        
        if ticker in self.known_funds:
            fund_data = self.known_funds[ticker]
            return {
                "asset_class": fund_data["asset_class"],
                "equity_region": fund_data.get("equity_region"),
                "equity_style": fund_data.get("equity_style"),
                "equity_size": fund_data.get("equity_size"),
                "fixed_income_type": fund_data.get("fixed_income_type"),
                "fixed_income_duration": fund_data.get("fixed_income_duration"),
                "reasoning": f"Known fund: {fund_data['description']}"
            }
        
        return None
    
    def _classify_by_rules(self, ticker: str, fund_name: str, provided_asset_class: str) -> Optional[Dict[str, Any]]:
        """Classify using rule-based patterns."""
        
        # Combine ticker and name for pattern matching
        search_text = f"{ticker} {fund_name}".lower()
        
        # Try each rule in priority order
        for rule in sorted(self.classification_rules, key=lambda r: r.priority):
            if re.search(rule.pattern, search_text, re.IGNORECASE):
                result = {
                    "asset_class": rule.asset_class,
                    "confidence": rule.confidence,
                    "reasoning": f"Matched pattern: {rule.pattern}"
                }
                
                # Add sub-categories from rule
                for key, value in rule.sub_categories.items():
                    result[key] = value
                
                return result
        
        # Fallback: use provided asset class if available
        if provided_asset_class and provided_asset_class.strip():
            return {
                "asset_class": self._normalize_asset_class(provided_asset_class),
                "confidence": 0.4,
                "reasoning": f"Using provided asset class: {provided_asset_class}"
            }
        
        return None
    
    def _classify_by_research(self, research_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Classify using research-based suggestions."""
        
        suggested_categories = research_data.get("suggested_categories", {})
        
        if not suggested_categories:
            return None
        
        # Get primary asset class suggestion
        asset_class_data = suggested_categories.get("asset_class")
        if not asset_class_data:
            return None
        
        result = {
            "asset_class": asset_class_data["suggestion"],
            "confidence": asset_class_data["confidence"],
            "reasoning": asset_class_data.get("reasoning", "Based on research analysis")
        }
        
        # Add sub-category suggestions
        for sub_cat in ["equity_style", "equity_size", "fixed_income_type"]:
            if sub_cat in suggested_categories:
                sub_data = suggested_categories[sub_cat]
                if sub_data:
                    result[sub_cat] = sub_data["suggestion"]
        
        return result
    
    def _classify_by_morningstar(self, morningstar_category: str) -> Optional[Dict[str, Any]]:
        """Classify using Morningstar category mapping."""
        
        category_lower = morningstar_category.lower()
        
        # Equity classifications
        if any(keyword in category_lower for keyword in ["equity", "stock", "large", "mid", "small"]):
            result = {
                "asset_class": "Equity",
                "reasoning": f"Morningstar category: {morningstar_category}"
            }
            
            # Determine size
            if "large" in category_lower:
                result["equity_size"] = "Large"
            elif "mid" in category_lower:
                result["equity_size"] = "Mid"
            elif "small" in category_lower:
                result["equity_size"] = "Small"
            
            # Determine style
            if "value" in category_lower:
                result["equity_style"] = "Value"
            elif "growth" in category_lower:
                result["equity_style"] = "Growth"
            elif "blend" in category_lower or "core" in category_lower:
                result["equity_style"] = "Blend"
            
            # Determine region
            if any(keyword in category_lower for keyword in ["us ", "domestic", "america"]):
                result["equity_region"] = "US"
            elif any(keyword in category_lower for keyword in ["international", "foreign", "europe", "pacific"]):
                result["equity_region"] = "International"
            elif any(keyword in category_lower for keyword in ["emerging", "frontier"]):
                result["equity_region"] = "Emerging"
            elif "global" in category_lower or "world" in category_lower:
                result["equity_region"] = "Global"
            
            return result
        
        # Fixed Income classifications
        elif any(keyword in category_lower for keyword in ["bond", "fixed", "income", "treasury", "corporate"]):
            result = {
                "asset_class": "Fixed Income",
                "reasoning": f"Morningstar category: {morningstar_category}"
            }
            
            # Determine type
            if "government" in category_lower or "treasury" in category_lower:
                result["fixed_income_type"] = "Government"
            elif "corporate" in category_lower:
                result["fixed_income_type"] = "Corporate"
            elif "municipal" in category_lower or "muni" in category_lower:
                result["fixed_income_type"] = "Municipal"
            elif "high yield" in category_lower or "junk" in category_lower:
                result["fixed_income_type"] = "High Yield"
            
            # Determine duration
            if "short" in category_lower:
                result["fixed_income_duration"] = "Short"
            elif "long" in category_lower:
                result["fixed_income_duration"] = "Long"
            elif any(keyword in category_lower for keyword in ["intermediate", "medium"]):
                result["fixed_income_duration"] = "Intermediate"
            
            return result
        
        # Alternative investments
        elif any(keyword in category_lower for keyword in ["commodity", "reit", "alternative", "hedge"]):
            return {
                "asset_class": "Alternatives",
                "reasoning": f"Morningstar category: {morningstar_category}"
            }
        
        # Cash and equivalents
        elif any(keyword in category_lower for keyword in ["money market", "cash", "stable value"]):
            return {
                "asset_class": "Cash",
                "reasoning": f"Morningstar category: {morningstar_category}"
            }
        
        return None
    
    def _normalize_asset_class(self, asset_class: str) -> Literal["Equity", "Fixed Income", "Cash", "Alternatives"]:
        """Normalize asset class string to standard format."""
        
        asset_class_lower = asset_class.lower().strip()
        
        if any(keyword in asset_class_lower for keyword in ["equity", "stock", "shares"]):
            return "Equity"
        elif any(keyword in asset_class_lower for keyword in ["bond", "fixed", "income", "debt"]):
            return "Fixed Income"
        elif any(keyword in asset_class_lower for keyword in ["cash", "money market", "stable"]):
            return "Cash"
        elif any(keyword in asset_class_lower for keyword in ["alternative", "commodity", "reit", "hedge"]):
            return "Alternatives"
        else:
            return "Equity"  # Default fallback
    
    def _calculate_asset_class_breakdown(self, classifications: List[ClassificationResult]) -> Dict[str, Dict[str, Any]]:
        """Calculate asset class distribution."""
        
        breakdown = defaultdict(lambda: {"count": 0, "confidence_sum": 0.0, "funds": []})
        
        for classification in classifications:
            asset_class = classification.asset_class
            breakdown[asset_class]["count"] += 1
            breakdown[asset_class]["confidence_sum"] += classification.asset_class_confidence
            breakdown[asset_class]["funds"].append(classification.ticker)
        
        # Calculate percentages and averages
        total_funds = len(classifications)
        result = {}
        
        for asset_class, data in breakdown.items():
            result[asset_class] = {
                "count": data["count"],
                "percentage": data["count"] / total_funds * 100,
                "avg_confidence": data["confidence_sum"] / data["count"],
                "funds": data["funds"]
            }
        
        return result
    
    def _determine_interaction_needs(self, classifications: List[ClassificationResult]) -> List[Dict[str, Any]]:
        """Determine which funds need user input."""
        
        interaction_needed = []
        
        for classification in classifications:
            needs_input = False
            reasons = []
            
            # Low confidence classifications need review
            if classification.asset_class_confidence < 0.7:
                needs_input = True
                reasons.append(f"Low confidence ({classification.asset_class_confidence:.1%})")
            
            # Missing important sub-categories for equity
            if classification.asset_class == "Equity":
                if not classification.equity_region:
                    needs_input = True
                    reasons.append("Missing region classification")
                if not classification.equity_style:
                    needs_input = True
                    reasons.append("Missing style classification")
                if not classification.equity_size:
                    needs_input = True
                    reasons.append("Missing size classification")
            
            # Missing important sub-categories for fixed income
            elif classification.asset_class == "Fixed Income":
                if not classification.fixed_income_type:
                    needs_input = True
                    reasons.append("Missing type classification")
                if not classification.fixed_income_duration:
                    needs_input = True
                    reasons.append("Missing duration classification")
            
            if needs_input:
                interaction_needed.append({
                    "ticker": classification.ticker,
                    "fund_name": classification.fund_name,
                    "reasons": reasons,
                    "current_classification": classification.to_dict(),
                    "suggested_questions": self._generate_questions(classification)
                })
        
        return interaction_needed
    
    def _generate_questions(self, classification: ClassificationResult) -> List[Dict[str, Any]]:
        """Generate questions for user interaction."""
        
        questions = []
        
        # Primary asset class question if low confidence
        if classification.asset_class_confidence < 0.7:
            questions.append({
                "type": "asset_class",
                "question": f"How should {classification.ticker} ({classification.fund_name}) be classified?",
                "options": [
                    {"value": "Equity", "label": "Equity", "recommended": classification.asset_class == "Equity"},
                    {"value": "Fixed Income", "label": "Fixed Income", "recommended": classification.asset_class == "Fixed Income"},
                    {"value": "Cash", "label": "Cash & Cash Equivalents", "recommended": classification.asset_class == "Cash"},
                    {"value": "Alternatives", "label": "Alternative Investments", "recommended": classification.asset_class == "Alternatives"}
                ],
                "confidence": classification.asset_class_confidence,
                "reasoning": classification.reasoning
            })
        
        # Equity sub-classification questions
        if classification.asset_class == "Equity":
            if not classification.equity_region:
                questions.append({
                    "type": "equity_region",
                    "question": f"What geographic region does {classification.ticker} focus on?",
                    "options": [
                        {"value": "US", "label": "United States"},
                        {"value": "International", "label": "International Developed"},
                        {"value": "Emerging", "label": "Emerging Markets"},
                        {"value": "Global", "label": "Global/World"}
                    ]
                })
            
            if not classification.equity_style:
                questions.append({
                    "type": "equity_style",
                    "question": f"What investment style does {classification.ticker} follow?",
                    "options": [
                        {"value": "Value", "label": "Value"},
                        {"value": "Growth", "label": "Growth"},
                        {"value": "Blend", "label": "Blend/Core"}
                    ]
                })
            
            if not classification.equity_size:
                questions.append({
                    "type": "equity_size",
                    "question": f"What market cap focus does {classification.ticker} have?",
                    "options": [
                        {"value": "Large", "label": "Large Cap"},
                        {"value": "Mid", "label": "Mid Cap"},
                        {"value": "Small", "label": "Small Cap"},
                        {"value": "Micro", "label": "Micro Cap"}
                    ]
                })
        
        # Fixed Income sub-classification questions
        elif classification.asset_class == "Fixed Income":
            if not classification.fixed_income_type:
                questions.append({
                    "type": "fixed_income_type",
                    "question": f"What type of bonds does {classification.ticker} hold?",
                    "options": [
                        {"value": "Government", "label": "Government/Treasury"},
                        {"value": "Corporate", "label": "Corporate"},
                        {"value": "Municipal", "label": "Municipal"},
                        {"value": "High Yield", "label": "High Yield/Junk"}
                    ]
                })
            
            if not classification.fixed_income_duration:
                questions.append({
                    "type": "fixed_income_duration",
                    "question": f"What duration focus does {classification.ticker} have?",
                    "options": [
                        {"value": "Short", "label": "Short Duration (< 3 years)"},
                        {"value": "Intermediate", "label": "Intermediate Duration (3-10 years)"},
                        {"value": "Long", "label": "Long Duration (> 10 years)"}
                    ]
                })
        
        return questions
    
    def _build_classification_rules(self) -> List[ClassificationRule]:
        """Build the rule-based classification system."""
        
        rules = [
            # Vanguard ETFs
            ClassificationRule(
                pattern=r"^VT[ISMX]",
                asset_class="Equity",
                sub_categories={"equity_region": "US", "equity_style": "Blend"},
                confidence=0.9,
                priority=1
            ),
            ClassificationRule(
                pattern=r"^VTV",
                asset_class="Equity", 
                sub_categories={"equity_region": "US", "equity_style": "Value"},
                confidence=0.9,
                priority=1
            ),
            ClassificationRule(
                pattern=r"^VUG",
                asset_class="Equity",
                sub_categories={"equity_region": "US", "equity_style": "Growth"},
                confidence=0.9,
                priority=1
            ),
            
            # iShares ETFs
            ClassificationRule(
                pattern=r"^IVV|^IWM|^IJR|^IJH",
                asset_class="Equity",
                sub_categories={"equity_region": "US"},
                confidence=0.85,
                priority=1
            ),
            
            # Bond ETFs
            ClassificationRule(
                pattern=r"bond|treasury|corporate.*bond|municipal.*bond",
                asset_class="Fixed Income",
                sub_categories={},
                confidence=0.8,
                priority=2
            ),
            
            # International/Emerging
            ClassificationRule(
                pattern=r"international|foreign|europe|asia|pacific|emerging|frontier",
                asset_class="Equity",
                sub_categories={"equity_region": "International"},
                confidence=0.7,
                priority=3
            ),
            
            # Sector/Alternative
            ClassificationRule(
                pattern=r"reit|commodity|gold|silver|oil|gas",
                asset_class="Alternatives",
                sub_categories={},
                confidence=0.75,
                priority=2
            ),
            
            # Money Market/Cash
            ClassificationRule(
                pattern=r"money.*market|cash|stable.*value|treasury.*bill",
                asset_class="Cash",
                sub_categories={},
                confidence=0.9,
                priority=1
            )
        ]
        
        return rules
    
    def _build_known_funds_database(self) -> Dict[str, Dict[str, Any]]:
        """Build database of well-known funds with definitive classifications."""
        
        return {
            # Vanguard Equity
            "VTI": {
                "asset_class": "Equity",
                "equity_region": "US",
                "equity_style": "Blend",
                "equity_size": "Large",
                "description": "Vanguard Total Stock Market ETF"
            },
            "VTV": {
                "asset_class": "Equity", 
                "equity_region": "US",
                "equity_style": "Value",
                "equity_size": "Large",
                "description": "Vanguard Value ETF"
            },
            "VUG": {
                "asset_class": "Equity",
                "equity_region": "US", 
                "equity_style": "Growth",
                "equity_size": "Large",
                "description": "Vanguard Growth ETF"
            },
            "VTSMX": {
                "asset_class": "Equity",
                "equity_region": "US",
                "equity_style": "Blend",
                "equity_size": "Large", 
                "description": "Vanguard Total Stock Market Index Fund"
            },
            
            # iShares
            "IVV": {
                "asset_class": "Equity",
                "equity_region": "US",
                "equity_style": "Blend", 
                "equity_size": "Large",
                "description": "iShares Core S&P 500 ETF"
            },
            "IWM": {
                "asset_class": "Equity",
                "equity_region": "US",
                "equity_style": "Blend",
                "equity_size": "Small", 
                "description": "iShares Russell 2000 ETF"
            },
            
            # Bond funds
            "BND": {
                "asset_class": "Fixed Income",
                "fixed_income_type": "Government",
                "fixed_income_duration": "Intermediate",
                "description": "Vanguard Total Bond Market ETF"
            },
            "AGG": {
                "asset_class": "Fixed Income", 
                "fixed_income_type": "Government",
                "fixed_income_duration": "Intermediate",
                "description": "iShares Core U.S. Aggregate Bond ETF"
            },
            
            # International
            "VTIAX": {
                "asset_class": "Equity",
                "equity_region": "International",
                "equity_style": "Blend",
                "equity_size": "Large",
                "description": "Vanguard Total International Stock Index Fund"
            },
            "EEM": {
                "asset_class": "Equity",
                "equity_region": "Emerging", 
                "equity_style": "Blend",
                "equity_size": "Large",
                "description": "iShares MSCI Emerging Markets ETF"
            },
            
            # Alternatives
            "GLD": {
                "asset_class": "Alternatives",
                "description": "SPDR Gold Shares"
            },
            "VNQ": {
                "asset_class": "Alternatives",
                "description": "Vanguard Real Estate ETF"
            }
        }
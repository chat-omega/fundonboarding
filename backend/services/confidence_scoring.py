"""Advanced confidence scoring algorithms for fund categorization system."""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict, Counter
import math

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceFactors:
    """Factors contributing to confidence scoring."""
    
    # Data source quality
    source_reliability: float = 0.0  # 0.0-1.0
    source_diversity: float = 0.0    # 0.0-1.0
    data_freshness: float = 0.0      # 0.0-1.0
    
    # Pattern matching strength
    pattern_match_score: float = 0.0  # 0.0-1.0
    pattern_specificity: float = 0.0  # 0.0-1.0
    
    # Cross-validation consistency
    method_agreement: float = 0.0     # 0.0-1.0
    historical_accuracy: float = 0.0  # 0.0-1.0
    
    # Data completeness and quality
    data_completeness: float = 0.0    # 0.0-1.0
    data_consistency: float = 0.0     # 0.0-1.0
    
    # Context and domain knowledge
    domain_specificity: float = 0.0   # 0.0-1.0
    contextual_coherence: float = 0.0 # 0.0-1.0
    
    def get_weighted_score(self, weights: Dict[str, float] = None) -> float:
        """Calculate weighted confidence score."""
        
        if weights is None:
            # Default weights based on importance
            weights = {
                "source_reliability": 0.20,
                "source_diversity": 0.10,
                "data_freshness": 0.05,
                "pattern_match_score": 0.15,
                "pattern_specificity": 0.10,
                "method_agreement": 0.15,
                "historical_accuracy": 0.10,
                "data_completeness": 0.10,
                "data_consistency": 0.10,
                "domain_specificity": 0.15,
                "contextual_coherence": 0.10
            }
        
        score = 0.0
        total_weight = 0.0
        
        for factor, weight in weights.items():
            if hasattr(self, factor):
                factor_value = getattr(self, factor)
                score += factor_value * weight
                total_weight += weight
        
        return score / total_weight if total_weight > 0 else 0.0


class ConfidenceScorer:
    """Advanced confidence scoring system for fund categorization."""
    
    def __init__(self):
        # Historical accuracy data (would be loaded from database in production)
        self.historical_accuracy = {
            "rule_based": 0.85,
            "known_fund": 0.98,
            "morningstar": 0.92,
            "research_based": 0.78,
            "pattern_matching": 0.65
        }
        
        # Source reliability ratings
        self.source_reliability = {
            "morningstar.com": 0.95,
            "vanguard.com": 0.98,
            "ishares.com": 0.98,
            "sec.gov": 0.99,
            "yahoo.finance": 0.75,
            "google.com": 0.40,
            "wikipedia.org": 0.30,
            "tavily": 0.70,
            "serper": 0.65,
            "duckduckgo": 0.50
        }
        
        # Pattern strength indicators
        self.pattern_strength = {
            "exact_ticker_match": 0.95,
            "fund_name_match": 0.85,
            "category_keyword": 0.70,
            "partial_match": 0.50,
            "inferred": 0.30
        }
        
        # Classification method reliability
        self.method_reliability = {
            "known_fund": 0.95,
            "morningstar_mapping": 0.90,
            "rule_based": 0.80,
            "research_synthesis": 0.75,
            "pattern_inference": 0.60,
            "fallback": 0.20
        }
    
    def calculate_classification_confidence(
        self, 
        classification_data: Dict[str, Any],
        research_data: Dict[str, Any] = None,
        validation_data: Dict[str, Any] = None
    ) -> Tuple[float, ConfidenceFactors]:
        """
        Calculate comprehensive confidence score for fund classification.
        
        Args:
            classification_data: Classification result data
            research_data: Research data used for classification  
            validation_data: Additional validation data
        
        Returns:
            Tuple of (confidence_score, confidence_factors)
        """
        
        factors = ConfidenceFactors()
        
        # 1. Source reliability assessment
        factors.source_reliability = self._assess_source_reliability(research_data or {})
        
        # 2. Source diversity assessment  
        factors.source_diversity = self._assess_source_diversity(research_data or {})
        
        # 3. Data freshness assessment
        factors.data_freshness = self._assess_data_freshness(research_data or {})
        
        # 4. Pattern matching strength
        factors.pattern_match_score = self._assess_pattern_strength(classification_data)
        
        # 5. Pattern specificity
        factors.pattern_specificity = self._assess_pattern_specificity(classification_data)
        
        # 6. Method agreement
        factors.method_agreement = self._assess_method_agreement(classification_data)
        
        # 7. Historical accuracy
        factors.historical_accuracy = self._assess_historical_accuracy(classification_data)
        
        # 8. Data completeness
        factors.data_completeness = self._assess_data_completeness(classification_data, research_data or {})
        
        # 9. Data consistency
        factors.data_consistency = self._assess_data_consistency(classification_data, research_data or {})
        
        # 10. Domain specificity
        factors.domain_specificity = self._assess_domain_specificity(classification_data)
        
        # 11. Contextual coherence  
        factors.contextual_coherence = self._assess_contextual_coherence(classification_data)
        
        # Calculate final weighted score
        confidence_score = factors.get_weighted_score()
        
        # Apply method-specific adjustments
        method_bonus = self._get_method_confidence_bonus(classification_data)
        confidence_score = min(1.0, confidence_score * (1.0 + method_bonus))
        
        # Apply consistency penalties
        consistency_penalty = self._calculate_consistency_penalty(classification_data)
        confidence_score = max(0.0, confidence_score - consistency_penalty)
        
        logger.debug(f"📊 Calculated confidence: {confidence_score:.3f} for {classification_data.get('ticker', 'unknown')}")
        
        return confidence_score, factors
    
    def _assess_source_reliability(self, research_data: Dict[str, Any]) -> float:
        """Assess reliability of research sources."""
        
        sources = research_data.get("research_sources", [])
        if not sources:
            return 0.3  # Default for no sources
        
        reliabilities = []
        
        for source in sources:
            source_lower = source.lower()
            
            # Check against known source reliability ratings
            reliability = 0.5  # Default
            
            for domain, rating in self.source_reliability.items():
                if domain in source_lower:
                    reliability = rating
                    break
            
            reliabilities.append(reliability)
        
        # Use weighted average (more sources = slightly higher confidence)
        avg_reliability = np.mean(reliabilities)
        source_diversity_bonus = min(0.1, len(sources) * 0.02)  # Up to 10% bonus
        
        return min(1.0, avg_reliability + source_diversity_bonus)
    
    def _assess_source_diversity(self, research_data: Dict[str, Any]) -> float:
        """Assess diversity of research sources."""
        
        sources = research_data.get("research_sources", [])
        if len(sources) <= 1:
            return 0.0 if len(sources) == 0 else 0.3
        
        # Analyze source types
        source_types = set()
        for source in sources:
            source_lower = source.lower()
            
            if any(domain in source_lower for domain in ["morningstar", "yahoo", "bloomberg"]):
                source_types.add("financial_data")
            elif any(domain in source_lower for domain in ["sec.gov", "regulatory"]):
                source_types.add("regulatory")
            elif any(domain in source_lower for domain in ["vanguard", "ishares", "fidelity"]):
                source_types.add("fund_company")
            elif any(domain in source_lower for domain in ["news", "reuters", "wsj"]):
                source_types.add("news")
            else:
                source_types.add("general")
        
        # Diversity score based on unique source types
        diversity_score = len(source_types) / 5.0  # Max 5 types
        
        # Bonus for multiple sources of same type (validation)
        total_sources_bonus = min(0.2, (len(sources) - 1) * 0.05)
        
        return min(1.0, diversity_score + total_sources_bonus)
    
    def _assess_data_freshness(self, research_data: Dict[str, Any]) -> float:
        """Assess freshness of research data."""
        
        data_points = research_data.get("data_points", {})
        if not data_points:
            return 0.5  # Neutral for no timestamp data
        
        now = datetime.now()
        freshness_scores = []
        
        for key, data_point in data_points.items():
            if isinstance(data_point, dict) and "extraction_timestamp" in data_point:
                try:
                    timestamp = datetime.fromisoformat(data_point["extraction_timestamp"])
                    age_hours = (now - timestamp).total_seconds() / 3600
                    
                    # Freshness decay function
                    if age_hours < 1:
                        freshness = 1.0
                    elif age_hours < 24:
                        freshness = 0.9
                    elif age_hours < 168:  # 1 week
                        freshness = 0.7
                    elif age_hours < 720:  # 1 month
                        freshness = 0.5
                    else:
                        freshness = 0.3
                    
                    freshness_scores.append(freshness)
                except:
                    freshness_scores.append(0.5)
        
        return np.mean(freshness_scores) if freshness_scores else 0.5
    
    def _assess_pattern_strength(self, classification_data: Dict[str, Any]) -> float:
        """Assess strength of pattern matching."""
        
        method = classification_data.get("classification_method", "unknown")
        reasoning = classification_data.get("reasoning", "").lower()
        
        # Base score from method reliability
        base_score = self.method_reliability.get(method, 0.5)
        
        # Pattern strength indicators
        strength_indicators = 0.0
        
        if "exact match" in reasoning:
            strength_indicators += 0.3
        elif "known fund" in reasoning:
            strength_indicators += 0.25
        elif "morningstar category" in reasoning:
            strength_indicators += 0.2
        elif "pattern" in reasoning:
            strength_indicators += 0.15
        elif "inferred" in reasoning:
            strength_indicators += 0.05
        
        # Ticker-specific patterns
        ticker = classification_data.get("ticker", "")
        if ticker:
            if re.match(r"^V[A-Z]{2,3}$", ticker):  # Vanguard pattern
                strength_indicators += 0.1
            elif re.match(r"^I[A-Z]{2,4}$", ticker):  # iShares pattern  
                strength_indicators += 0.1
        
        return min(1.0, base_score + strength_indicators)
    
    def _assess_pattern_specificity(self, classification_data: Dict[str, Any]) -> float:
        """Assess specificity of classification patterns."""
        
        asset_class = classification_data.get("asset_class", "")
        sub_categories = 0
        
        # Count filled sub-categories
        for field in ["equity_region", "equity_style", "equity_size", "fixed_income_type", "fixed_income_duration"]:
            if classification_data.get(field):
                sub_categories += 1
        
        # Base specificity from asset class clarity
        asset_class_specificity = {
            "Equity": 0.7,
            "Fixed Income": 0.7,
            "Cash": 0.9,  # Very specific
            "Alternatives": 0.6
        }.get(asset_class, 0.3)
        
        # Bonus for sub-category specificity
        sub_category_bonus = min(0.3, sub_categories * 0.1)
        
        return min(1.0, asset_class_specificity + sub_category_bonus)
    
    def _assess_method_agreement(self, classification_data: Dict[str, Any]) -> float:
        """Assess agreement between different classification methods."""
        
        alternatives = classification_data.get("alternative_classifications", [])
        
        if not alternatives:
            return 0.5  # Neutral when no alternatives
        
        primary_asset_class = classification_data.get("asset_class")
        
        # Count how many alternatives agree with primary classification
        agreements = 0
        total_alternatives = len(alternatives)
        
        for alt in alternatives:
            if alt.get("asset_class") == primary_asset_class:
                agreements += 1
        
        agreement_ratio = agreements / total_alternatives if total_alternatives > 0 else 0.5
        
        # Bonus for having multiple methods agree
        consensus_bonus = 0.0
        if agreement_ratio >= 0.8:
            consensus_bonus = 0.2
        elif agreement_ratio >= 0.6:
            consensus_bonus = 0.1
        
        return min(1.0, agreement_ratio + consensus_bonus)
    
    def _assess_historical_accuracy(self, classification_data: Dict[str, Any]) -> float:
        """Assess historical accuracy of classification method."""
        
        method = classification_data.get("classification_method", "unknown")
        return self.historical_accuracy.get(method, 0.5)
    
    def _assess_data_completeness(self, classification_data: Dict[str, Any], research_data: Dict[str, Any]) -> float:
        """Assess completeness of available data."""
        
        # Key fields that should be present
        important_fields = [
            "asset_class",
            "ticker",
            "fund_name",
            "classification_method",
            "reasoning"
        ]
        
        # Research data fields
        research_fields = [
            "morningstar_category",
            "expense_ratio",
            "holdings_text"
        ]
        
        filled_important = sum(1 for field in important_fields if classification_data.get(field))
        completeness_core = filled_important / len(important_fields)
        
        # Research data completeness
        data_points = research_data.get("data_points", {})
        filled_research = sum(1 for field in research_fields if field in data_points)
        completeness_research = filled_research / len(research_fields) if research_fields else 0.0
        
        # Sub-category completeness based on asset class
        sub_completeness = self._assess_subcategory_completeness(classification_data)
        
        # Weighted combination
        overall_completeness = (
            completeness_core * 0.5 +
            completeness_research * 0.3 + 
            sub_completeness * 0.2
        )
        
        return min(1.0, overall_completeness)
    
    def _assess_subcategory_completeness(self, classification_data: Dict[str, Any]) -> float:
        """Assess completeness of sub-categorization."""
        
        asset_class = classification_data.get("asset_class", "")
        
        if asset_class == "Equity":
            equity_fields = ["equity_region", "equity_style", "equity_size"]
            filled = sum(1 for field in equity_fields if classification_data.get(field))
            return filled / len(equity_fields)
        
        elif asset_class == "Fixed Income":
            fixed_income_fields = ["fixed_income_type", "fixed_income_duration"]
            filled = sum(1 for field in fixed_income_fields if classification_data.get(field))
            return filled / len(fixed_income_fields)
        
        else:
            # Cash and Alternatives don't need sub-categories
            return 1.0
    
    def _assess_data_consistency(self, classification_data: Dict[str, Any], research_data: Dict[str, Any]) -> float:
        """Assess consistency of data across sources."""
        
        data_points = research_data.get("data_points", {})
        if not data_points:
            return 0.5  # Neutral when no data to check consistency
        
        consistency_checks = []
        
        # Check morningstar category consistency with asset class
        if "morningstar_category" in data_points:
            morningstar_cat = data_points["morningstar_category"]["value"].lower()
            asset_class = classification_data.get("asset_class", "").lower()
            
            if asset_class == "equity":
                consistent = any(keyword in morningstar_cat for keyword in ["equity", "stock", "large", "mid", "small"])
            elif asset_class == "fixed income":
                consistent = any(keyword in morningstar_cat for keyword in ["bond", "fixed", "income"])
            else:
                consistent = True  # Can't easily check others
                
            consistency_checks.append(1.0 if consistent else 0.0)
        
        # Check expense ratio reasonableness
        if "expense_ratio" in data_points:
            expense_ratio = data_points["expense_ratio"]["value"]
            if isinstance(expense_ratio, (int, float)):
                # Reasonable expense ratio check (0-3%)
                reasonable = 0.0 <= expense_ratio <= 0.03
                consistency_checks.append(1.0 if reasonable else 0.5)
        
        # Return average consistency
        return np.mean(consistency_checks) if consistency_checks else 0.5
    
    def _assess_domain_specificity(self, classification_data: Dict[str, Any]) -> float:
        """Assess domain-specific knowledge application."""
        
        ticker = classification_data.get("ticker", "")
        fund_name = classification_data.get("fund_name", "").lower()
        reasoning = classification_data.get("reasoning", "").lower()
        
        domain_score = 0.5  # Base score
        
        # Fund family recognition
        if any(family in fund_name for family in ["vanguard", "ishares", "fidelity", "schwab"]):
            domain_score += 0.1
        
        # Fund type recognition in name
        if any(type_word in fund_name for type_word in ["etf", "index", "mutual fund", "trust"]):
            domain_score += 0.1
        
        # Market segment recognition
        if any(segment in fund_name for segment in ["total market", "s&p 500", "russell", "msci"]):
            domain_score += 0.1
        
        # Geographic recognition
        if any(geo in fund_name for geo in ["international", "emerging", "global", "europe", "asia"]):
            domain_score += 0.1
        
        # Sector/style recognition
        if any(style in fund_name for style in ["value", "growth", "dividend", "small cap", "large cap"]):
            domain_score += 0.1
        
        return min(1.0, domain_score)
    
    def _assess_contextual_coherence(self, classification_data: Dict[str, Any]) -> float:
        """Assess coherence of classification within context."""
        
        asset_class = classification_data.get("asset_class", "")
        sub_categories = {}
        
        # Gather sub-categories
        if asset_class == "Equity":
            sub_categories = {
                "region": classification_data.get("equity_region"),
                "style": classification_data.get("equity_style"), 
                "size": classification_data.get("equity_size")
            }
        elif asset_class == "Fixed Income":
            sub_categories = {
                "type": classification_data.get("fixed_income_type"),
                "duration": classification_data.get("fixed_income_duration")
            }
        
        # Check logical coherence
        coherence_score = 0.7  # Base coherence
        
        # Asset class and sub-category coherence
        if asset_class == "Equity" and sub_categories.get("region") == "US":
            coherence_score += 0.1  # US equity is common and coherent
        
        if asset_class == "Fixed Income" and sub_categories.get("type") == "Government":
            coherence_score += 0.1  # Government bonds are coherent category
        
        # Check for contradictions
        fund_name = classification_data.get("fund_name", "").lower()
        
        if asset_class == "Equity" and "bond" in fund_name:
            coherence_score -= 0.3  # Contradiction
        elif asset_class == "Fixed Income" and any(word in fund_name for word in ["equity", "stock"]):
            coherence_score -= 0.3  # Contradiction
        
        return max(0.0, min(1.0, coherence_score))
    
    def _get_method_confidence_bonus(self, classification_data: Dict[str, Any]) -> float:
        """Get confidence bonus based on classification method."""
        
        method = classification_data.get("classification_method", "")
        
        bonuses = {
            "known_fund": 0.1,
            "morningstar": 0.05,
            "rule_based": 0.0,
            "research_based": -0.05,  # Slightly penalize less reliable methods
        }
        
        return bonuses.get(method, 0.0)
    
    def _calculate_consistency_penalty(self, classification_data: Dict[str, Any]) -> float:
        """Calculate penalty for inconsistent data."""
        
        penalty = 0.0
        
        # Check for obvious inconsistencies
        asset_class = classification_data.get("asset_class", "")
        fund_name = classification_data.get("fund_name", "").lower()
        
        # Name-classification mismatches
        if asset_class == "Fixed Income" and any(word in fund_name for word in ["equity", "stock", "shares"]):
            penalty += 0.2
        elif asset_class == "Equity" and any(word in fund_name for word in ["bond", "treasury", "fixed income"]):
            penalty += 0.2
        
        # Sub-category inconsistencies
        if asset_class == "Equity":
            region = classification_data.get("equity_region")
            if region == "US" and any(word in fund_name for word in ["international", "foreign", "global"]):
                penalty += 0.1
            elif region == "International" and "us " in fund_name:
                penalty += 0.1
        
        return penalty
    
    def calculate_portfolio_confidence(self, classifications: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate portfolio-level confidence metrics."""
        
        if not classifications:
            return {"overall": 0.0, "average": 0.0, "min": 0.0, "max": 0.0}
        
        confidences = [c.get("asset_class_confidence", 0.0) for c in classifications]
        
        return {
            "overall": np.mean(confidences),
            "average": np.mean(confidences),
            "min": np.min(confidences),
            "max": np.max(confidences),
            "std": np.std(confidences),
            "high_confidence_ratio": len([c for c in confidences if c >= 0.8]) / len(confidences)
        }
    
    def get_confidence_explanation(self, confidence_score: float, factors: ConfidenceFactors) -> str:
        """Generate human-readable explanation of confidence score."""
        
        explanations = []
        
        if confidence_score >= 0.9:
            explanations.append("Very high confidence")
        elif confidence_score >= 0.8:
            explanations.append("High confidence")
        elif confidence_score >= 0.6:
            explanations.append("Moderate confidence")
        elif confidence_score >= 0.4:
            explanations.append("Low confidence")
        else:
            explanations.append("Very low confidence")
        
        # Add key contributing factors
        if factors.source_reliability > 0.8:
            explanations.append("reliable data sources")
        if factors.method_agreement > 0.7:
            explanations.append("multiple methods agree")
        if factors.pattern_match_score > 0.8:
            explanations.append("strong pattern match")
        if factors.data_completeness > 0.8:
            explanations.append("comprehensive data available")
        
        # Add concerns
        if factors.source_reliability < 0.5:
            explanations.append("limited source reliability")
        if factors.data_completeness < 0.5:
            explanations.append("incomplete data")
        if factors.data_consistency < 0.5:
            explanations.append("inconsistent information")
        
        return " - ".join(explanations)


# Global confidence scorer instance
confidence_scorer = ConfidenceScorer()
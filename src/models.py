"""Data models for fund extraction."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class FundData(BaseModel):
    """Concise fund data extraction schema optimized for LLM extraction"""

    # Identifiers
    fund_name: str = Field(
        ...,
        description="Full fund name exactly as it appears, e.g. 'Vanguard Total Stock Market ETF' or 'Fidelity Asset Manager® 20%'",
    )
    ticker: Optional[str] = Field(
        None,
        description="Fund ticker symbol, e.g. 'VTI', 'VTV', 'VUG' for ETFs",
    )
    fund_type: Optional[str] = Field(
        None,
        description="Type of fund: 'ETF', 'Mutual Fund', 'Index Fund', etc.",
    )
    target_equity_pct: Optional[int] = Field(
        None,
        description="Target equity percentage from fund name (20, 30, 40, 50, 60, 70, or 85)",
    )
    report_date: Optional[str] = Field(
        None, description="Report date in YYYY-MM-DD format, e.g. '2024-09-30'"
    )
    inception_date: Optional[str] = Field(
        None, description="Fund inception date in YYYY-MM-DD format"
    )
    
    # ETF-specific fields
    shares_outstanding: Optional[float] = Field(
        None, description="Number of shares outstanding for ETFs"
    )
    market_price: Optional[float] = Field(
        None, description="Market price per share for ETFs"
    )
    premium_discount: Optional[float] = Field(
        None, description="Premium/discount percentage relative to NAV for ETFs"
    )
    bid_ask_spread: Optional[float] = Field(
        None, description="Bid-ask spread for ETF trading"
    )
    dividend_yield: Optional[float] = Field(
        None, description="Dividend yield percentage"
    )
    distribution_frequency: Optional[str] = Field(
        None, description="Distribution frequency: 'Monthly', 'Quarterly', 'Annually', etc."
    )

    # Asset Allocation (as percentages, e.g. 27.4 for 27.4%)
    equity_pct: Optional[float] = Field(
        None,
        description="Equity allocation percentage from portfolio composition or holdings breakdown",
    )
    fixed_income_pct: Optional[float] = Field(
        None,
        description="Fixed income/bonds allocation percentage from portfolio composition",
    )
    money_market_pct: Optional[float] = Field(
        None,
        description="Money market/cash allocation percentage from portfolio composition",
    )
    other_pct: Optional[float] = Field(
        None,
        description="Other investments percentage (alternatives, commodities, etc.)",
    )

    # Primary Share Class Metrics (use the main retail class, usually named after the fund)
    nav: Optional[float] = Field(
        None,
        description="Net Asset Value per share for the main retail class (e.g. Asset Manager 20% class)",
    )
    net_assets_usd: Optional[float] = Field(
        None,
        description="Total net assets in USD for the main retail class from 'Net Asset Value' section",
    )
    expense_ratio: Optional[float] = Field(
        None,
        description="Expense ratio as percentage (e.g. 0.48 for 0.48%) from Financial Highlights",
    )
    management_fee: Optional[float] = Field(
        None,
        description="Management fee rate as percentage from Financial Highlights or Notes",
    )

    # Performance (as percentages)
    one_year_return: Optional[float] = Field(
        None,
        description="One-year total return percentage from Financial Highlights (e.g. 13.74 for 13.74%)",
    )
    portfolio_turnover: Optional[float] = Field(
        None, description="Portfolio turnover rate percentage from Financial Highlights"
    )

    # Risk Metrics (in USD)
    equity_futures_notional: Optional[float] = Field(
        None,
        description="Net notional amount of equity futures contracts (positive if net long, negative if net short)",
    )
    bond_futures_notional: Optional[float] = Field(
        None,
        description="Net notional amount of bond/treasury futures contracts (positive if net long, negative if net short)",
    )

    # Fund Flows (in USD)
    net_investment_income: Optional[float] = Field(
        None,
        description="Net investment income for the period from Statement of Operations",
    )
    total_distributions: Optional[float] = Field(
        None,
        description="Total distributions to shareholders from Statement of Changes in Net Assets",
    )
    net_asset_change: Optional[float] = Field(
        None,
        description="Net change in assets from beginning to end of period (end minus beginning net assets)",
    )
    
    # Holdings and Allocation Information
    number_of_holdings: Optional[int] = Field(
        None, description="Total number of holdings in the fund"
    )
    top_10_holdings: Optional[List[str]] = Field(
        None, description="List of top 10 holdings with percentages"
    )
    sector_allocation: Optional[List[str]] = Field(
        None, description="List of sector allocations with percentages"
    )
    geographic_allocation: Optional[List[str]] = Field(
        None, description="List of geographic/country allocations with percentages"
    )
    
    # Additional Fund Information
    fund_manager: Optional[str] = Field(
        None, description="Fund manager or management team"
    )
    management_company: Optional[str] = Field(
        None, description="Management company or fund family"
    )
    benchmark: Optional[str] = Field(
        None, description="Primary benchmark index"
    )
    investment_objective: Optional[str] = Field(
        None, description="Fund's investment objective or strategy description"
    )
    minimum_investment: Optional[float] = Field(
        None, description="Minimum initial investment amount"
    )


class FundComparisonData(BaseModel):
    """Flattened data optimized for CSV export and analysis"""

    funds: List[FundData]

    def to_csv_rows(self) -> List[dict]:
        """Convert to list of dictionaries for CSV export"""
        return [fund.dict() for fund in self.funds]


class SplitCategories(BaseModel):
    """A list of all split categories from a document."""

    split_categories: List[str]


class SplitOutput(BaseModel):
    """The metadata for a given split start given a chunk."""

    split_name: str = Field(
        ..., description="The name of the split (in the format \\{split_key\\}_X)"
    )
    split_description: str = Field(
        ..., description="A short description corresponding to the split."
    )
    page_number: int = Field(..., description="Page number of the split.")


class SplitsOutput(BaseModel):
    """A list of all splits given a chunk."""

    splits: List[SplitOutput]
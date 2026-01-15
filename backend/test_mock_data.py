#!/usr/bin/env python3
"""Test the web UI with mock fund data."""

import json
import asyncio
from fastapi.testclient import TestClient
from main import app

# Mock fund data that resembles real Fidelity fund extraction results
MOCK_FUND_DATA = [
    {
        "fund_name": "Fidelity Blue Chip Growth Fund",
        "target_equity_pct": 85.0,
        "report_date": "2024-01-31",
        "equity_pct": 87.2,
        "fixed_income_pct": 8.5,
        "money_market_pct": 4.1,
        "other_pct": 0.2,
        "nav": 142.85,
        "net_assets_usd": 15600000000,
        "expense_ratio": 0.68,
        "management_fee": 0.55,
        "one_year_return": 12.4,
        "portfolio_turnover": 23.0,
        "equity_futures_notional": 125000000,
        "bond_futures_notional": 0,
        "net_investment_income": 245000000,
        "total_distributions": 890000000,
        "net_asset_change": 1200000000,
        "return_per_risk": 18.2,
        "drift": 2.2
    },
    {
        "fund_name": "Fidelity Contrafund",
        "target_equity_pct": 90.0,
        "report_date": "2024-01-31",
        "equity_pct": 91.8,
        "fixed_income_pct": 5.2,
        "money_market_pct": 3.0,
        "other_pct": 0.0,
        "nav": 18.92,
        "net_assets_usd": 118500000000,
        "expense_ratio": 0.85,
        "management_fee": 0.75,
        "one_year_return": 8.7,
        "portfolio_turnover": 41.0,
        "equity_futures_notional": 2400000000,
        "bond_futures_notional": 0,
        "net_investment_income": 1240000000,
        "total_distributions": 3200000000,
        "net_asset_change": -2100000000,
        "return_per_risk": 10.2,
        "drift": 1.8
    },
    {
        "fund_name": "Fidelity International Growth Fund",
        "target_equity_pct": 95.0,
        "report_date": "2024-01-31",
        "equity_pct": 94.1,
        "fixed_income_pct": 2.8,
        "money_market_pct": 2.9,
        "other_pct": 0.2,
        "nav": 24.17,
        "net_assets_usd": 8900000000,
        "expense_ratio": 1.12,
        "management_fee": 1.00,
        "one_year_return": -3.2,
        "portfolio_turnover": 67.0,
        "equity_futures_notional": 450000000,
        "bond_futures_notional": 0,
        "net_investment_income": 180000000,
        "total_distributions": 220000000,
        "net_asset_change": -890000000,
        "return_per_risk": -2.9,
        "drift": -0.9
    },
    {
        "fund_name": "Fidelity Balanced Fund",
        "target_equity_pct": 60.0,
        "report_date": "2024-01-31",
        "equity_pct": 62.4,
        "fixed_income_pct": 35.1,
        "money_market_pct": 2.5,
        "other_pct": 0.0,
        "nav": 26.94,
        "net_assets_usd": 24700000000,
        "expense_ratio": 0.52,
        "management_fee": 0.42,
        "one_year_return": 6.8,
        "portfolio_turnover": 18.0,
        "equity_futures_notional": 125000000,
        "bond_futures_notional": 890000000,
        "net_investment_income": 720000000,
        "total_distributions": 1100000000,
        "net_asset_change": 450000000,
        "return_per_risk": 13.1,
        "drift": 2.4
    },
    {
        "fund_name": "Fidelity Freedom 2050 Fund",
        "target_equity_pct": 90.0,
        "report_date": "2024-01-31",
        "equity_pct": 89.7,
        "fixed_income_pct": 10.0,
        "money_market_pct": 0.3,
        "other_pct": 0.0,
        "nav": 17.85,
        "net_assets_usd": 45200000000,
        "expense_ratio": 0.12,
        "management_fee": 0.08,
        "one_year_return": 15.2,
        "portfolio_turnover": 5.0,
        "equity_futures_notional": 0,
        "bond_futures_notional": 0,
        "net_investment_income": 450000000,
        "total_distributions": 890000000,
        "net_asset_change": 3400000000,
        "return_per_risk": 126.7,
        "drift": -0.3
    },
    {
        "fund_name": "Fidelity Small Cap Growth Fund",
        "target_equity_pct": 95.0,
        "report_date": "2024-01-31",
        "equity_pct": 96.2,
        "fixed_income_pct": 0.8,
        "money_market_pct": 3.0,
        "other_pct": 0.0,
        "nav": 31.47,
        "net_assets_usd": 6700000000,
        "expense_ratio": 0.97,
        "management_fee": 0.86,
        "one_year_return": 22.1,
        "portfolio_turnover": 89.0,
        "equity_futures_notional": 245000000,
        "bond_futures_notional": 0,
        "net_investment_income": 45000000,
        "total_distributions": 125000000,
        "net_asset_change": 890000000,
        "return_per_risk": 22.8,
        "drift": 1.2
    }
]

def create_mock_events():
    """Create mock SSE events for testing."""
    events = []
    
    # Setup events
    events.append({"type": "text", "data": {"content": "🔧 Initializing Fund Extraction Agent (Mock Mode)..."}})
    events.append({"type": "status", "data": {"stage": "setup", "progress": 10, "message": "Setting up mock extraction..."}})
    
    # Parsing events
    events.append({"type": "text", "data": {"content": "📄 Processing mock PDF document..."}})
    events.append({"type": "status", "data": {"stage": "parsing", "progress": 30, "message": "Parsing PDF document..."}})
    events.append({"type": "text", "data": {"content": "✓ Parsed 120 pages (simulated)"}})
    
    # Splitting events
    events.append({"type": "status", "data": {"stage": "splitting", "progress": 50, "message": "Identifying fund sections..."}})
    events.append({"type": "text", "data": {"content": "🔍 Found 6 fund sections"}})
    
    # Discovery events
    for i, fund in enumerate(MOCK_FUND_DATA, 1):
        events.append({
            "type": "fund_discovered", 
            "data": {
                "fund_name": fund["fund_name"],
                "page_count": 18 + i * 2
            }
        })
    
    # Extraction events
    events.append({"type": "status", "data": {"stage": "extracting", "progress": 70, "message": "Extracting fund data..."}})
    
    for fund in MOCK_FUND_DATA:
        events.append({
            "type": "fund_extracted",
            "data": {"fund": fund}
        })
        events.append({"type": "text", "data": {"content": f"📋 Extracted: {fund['fund_name']}"}})
    
    # Analysis events
    events.append({"type": "status", "data": {"stage": "analysis", "progress": 90, "message": "Analyzing fund data..."}})
    events.append({"type": "text", "data": {"content": "📊 Computing performance metrics..."}})
    
    # Completion
    events.append({"type": "status", "data": {"stage": "complete", "progress": 100, "message": "Extraction completed!"}})
    events.append({
        "type": "results",
        "data": {
            "funds": MOCK_FUND_DATA,
            "summary": {
                "total_funds": len(MOCK_FUND_DATA),
                "pages_processed": 120,
                "fund_sections": [f["fund_name"] for f in MOCK_FUND_DATA],
                "session_id": "mock-session-123"
            }
        }
    })
    
    return events

def print_mock_events():
    """Print mock events in SSE format."""
    events = create_mock_events()
    
    for event in events:
        print(f"data: {json.dumps(event)}")
        print()

if __name__ == "__main__":
    print("Mock Fund Extraction Events (SSE Format):")
    print("=" * 50)
    print_mock_events()
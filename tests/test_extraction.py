"""Test script for fund extraction functionality."""

import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from config import config
from src.models import FundData, SplitCategories
from src.split_detector import afind_split_categories
from llama_index.llms.openai import OpenAI
from llama_index.core.schema import TextNode


def test_config():
    """Test configuration validation."""
    print("Testing configuration...")
    
    # Test config validation
    is_valid = config.validate()
    print(f"Configuration valid: {is_valid}")
    
    if not is_valid:
        print("Please update .env file with actual API keys")
        return False
    
    print("✓ Configuration test passed")
    return True


def test_models():
    """Test Pydantic models."""
    print("Testing data models...")
    
    # Test FundData model
    sample_fund = FundData(
        fund_name="Test Fund 20%",
        target_equity_pct=20,
        equity_pct=19.5,
        nav=10.50
    )
    
    print(f"Created sample fund: {sample_fund.fund_name}")
    print(f"Sample fund dict: {sample_fund.dict()}")
    
    # Test SplitCategories model  
    sample_categories = SplitCategories(
        split_categories=["Fund A", "Fund B", "Fund C"]
    )
    
    print(f"Created sample categories: {sample_categories.split_categories}")
    
    print("✓ Models test passed")
    return True


async def test_split_detection():
    """Test split detection with sample data."""
    print("Testing split detection...")
    
    # Create sample nodes
    sample_nodes = [
        TextNode(
            text="Table of Contents\nFidelity Asset Manager 20%\nFidelity Asset Manager 30%",
            metadata={"page_number": 1}
        ),
        TextNode(
            text="Fidelity Asset Manager 20%\nSchedule of Investments",
            metadata={"page_number": 2}
        )
    ]
    
    try:
        config.setup_environment()
        llm = OpenAI(model="gpt-4o")
        
        categories = await afind_split_categories(
            "Find and split by the main funds in this document",
            sample_nodes,
            llm=llm,
            page_limit=2
        )
        
        print(f"Found categories: {categories}")
        print("✓ Split detection test passed")
        return True
        
    except Exception as e:
        print(f"Split detection test failed: {e}")
        return False


def run_basic_tests():
    """Run basic non-async tests."""
    print("="*50)
    print("Running basic tests...")
    print("="*50)
    
    tests_passed = 0
    total_tests = 2
    
    if test_config():
        tests_passed += 1
    
    if test_models():
        tests_passed += 1
        
    print(f"\nBasic tests: {tests_passed}/{total_tests} passed")
    return tests_passed == total_tests


async def run_async_tests():
    """Run async tests that require API calls."""
    print("="*50)
    print("Running async tests...")
    print("="*50)
    
    tests_passed = 0
    total_tests = 1
    
    if await test_split_detection():
        tests_passed += 1
        
    print(f"\nAsync tests: {tests_passed}/{total_tests} passed")
    return tests_passed == total_tests


async def main():
    """Run all tests."""
    print("Starting fund extraction tests...")
    
    # Run basic tests first
    basic_passed = run_basic_tests()
    
    if not basic_passed:
        print("\nBasic tests failed. Skipping async tests.")
        return False
    
    # Run async tests if basic tests pass
    async_passed = await run_async_tests()
    
    overall_success = basic_passed and async_passed
    
    print("="*50)
    print(f"Overall test result: {'PASSED' if overall_success else 'FAILED'}")
    print("="*50)
    
    return overall_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Test script for the new Gemini extraction system.
This script tests the Docling + Gemini extraction pipeline.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.append('./backend')
sys.path.append('.')

async def test_basic_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        from backend.gemini_extraction_service import (
            check_dependencies, 
            GeminiExtractionService,
            DoclingParser,
            GeminiExtractor
        )
        print("✅ Gemini extraction service imports successful")
        
        # Check dependencies
        deps = check_dependencies()
        print(f"📋 Dependencies check:")
        for name, available in deps.items():
            status = "✅" if available else "❌"
            print(f"   {status} {name}")
        
        return all(deps.values())
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_docling_parsing():
    """Test Docling PDF parsing."""
    print("\n📄 Testing Docling PDF parsing...")
    
    try:
        from backend.gemini_extraction_service import DoclingParser
        
        # Test with a sample PDF
        test_pdf = "./data/VTI.pdf"
        if not Path(test_pdf).exists():
            print(f"❌ Test PDF not found: {test_pdf}")
            return False
        
        parser = DoclingParser()
        result = parser.parse_document(test_pdf)
        
        if result.success:
            print(f"✅ Successfully parsed {test_pdf}")
            print(f"   📊 Markdown length: {len(result.markdown_content):,} chars")
            print(f"   📋 Tables extracted: {len(result.tables_markdown)}")
            print(f"   📖 Estimated pages: {result.page_count}")
            
            # Show a snippet of the markdown
            snippet = result.markdown_content[:200] + "..." if len(result.markdown_content) > 200 else result.markdown_content
            print(f"   📝 Markdown preview: {snippet}")
            
            return True
        else:
            print(f"❌ Parsing failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ Docling parsing error: {e}")
        return False


async def test_gemini_extraction():
    """Test the full Gemini extraction pipeline."""
    print("\n🤖 Testing Gemini extraction...")
    
    try:
        from backend.gemini_extraction_service import GeminiExtractionService
        
        # Check if Gemini API key is set
        if not os.getenv("GEMINI_API_KEY"):
            print("⚠️ GEMINI_API_KEY not set - skipping Gemini test")
            print("   Set GEMINI_API_KEY environment variable to test Gemini extraction")
            return True
        
        # Test with a sample PDF
        test_pdf = "./data/VTI.pdf"
        if not Path(test_pdf).exists():
            print(f"❌ Test PDF not found: {test_pdf}")
            return False
        
        service = GeminiExtractionService()
        
        print(f"   🔄 Processing {test_pdf}...")
        start_time = time.time()
        
        result = await service.extract_fund(test_pdf)
        
        elapsed = time.time() - start_time
        
        if result.success:
            fund_data = result.fund_data
            print(f"✅ Extraction successful in {elapsed:.2f}s")
            print(f"   📊 Confidence: {result.confidence_score:.2f}")
            print(f"   📄 Markdown length: {result.markdown_length:,} chars")
            print(f"   📋 Tables extracted: {result.tables_extracted}")
            
            print(f"\n   📈 Extracted fund data:")
            print(f"      Fund name: {fund_data.fund_name}")
            print(f"      Ticker: {fund_data.ticker}")
            print(f"      Fund type: {fund_data.fund_type}")
            print(f"      NAV: ${fund_data.nav}")
            print(f"      Expense ratio: {fund_data.expense_ratio}%")
            print(f"      1-year return: {fund_data.one_year_return}%")
            print(f"      Equity allocation: {fund_data.equity_pct}%")
            
            if result.warnings:
                print(f"   ⚠️ Warnings ({len(result.warnings)}):")
                for warning in result.warnings:
                    print(f"      - {warning}")
            
            return True
        else:
            print(f"❌ Extraction failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ Gemini extraction error: {e}")
        return False


async def test_unified_service():
    """Test the unified extraction service routing."""
    print("\n🔄 Testing unified extraction service...")
    
    try:
        from backend.extraction_service import extraction_service
        
        # Test with multiple PDFs
        test_pdfs = ["./data/VTI.pdf", "./data/VTV.pdf"]
        available_pdfs = [pdf for pdf in test_pdfs if Path(pdf).exists()]
        
        if not available_pdfs:
            print("❌ No test PDFs found")
            return False
        
        print(f"   📄 Testing with {len(available_pdfs)} PDFs: {[Path(p).name for p in available_pdfs]}")
        
        results = await extraction_service.extract_multiple_funds(available_pdfs)
        
        successful = sum(1 for r in results if r.success)
        print(f"   ✅ {successful}/{len(results)} extractions successful")
        
        for i, result in enumerate(results):
            pdf_name = Path(available_pdfs[i]).name
            if result.success:
                print(f"      ✅ {pdf_name}: {result.fund_data.fund_name} ({result.method_used}, {result.confidence_score:.2f})")
            else:
                print(f"      ❌ {pdf_name}: {result.error}")
        
        return successful > 0
        
    except Exception as e:
        print(f"❌ Unified service error: {e}")
        return False


async def main():
    """Run all tests."""
    print("🧪 Gemini Extraction System Test Suite")
    print("=" * 50)
    
    test_results = []
    
    # Test 1: Basic imports
    result1 = await test_basic_imports()
    test_results.append(("Basic imports", result1))
    
    # Test 2: Docling parsing
    result2 = await test_docling_parsing()
    test_results.append(("Docling parsing", result2))
    
    # Test 3: Gemini extraction (only if API key is available)
    result3 = await test_gemini_extraction()
    test_results.append(("Gemini extraction", result3))
    
    # Test 4: Unified service
    result4 = await test_unified_service()
    test_results.append(("Unified service", result4))
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 30)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(test_results)} tests passed")
    
    if passed == len(test_results):
        print("\n🎉 All tests passed! Gemini extraction system is ready to use.")
    elif passed > 0:
        print("\n⚠️ Some tests passed. Check the failures above.")
    else:
        print("\n❌ All tests failed. Check your setup and dependencies.")
    
    return passed == len(test_results)


if __name__ == "__main__":
    # Run the test suite
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
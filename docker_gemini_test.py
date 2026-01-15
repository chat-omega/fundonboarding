#!/usr/bin/env python3
"""
Simplified Docker test for Gemini extraction.
"""

import os
import sys
import asyncio
import time
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, '/app')

async def test_gemini_extraction():
    """Test complete Gemini extraction pipeline in Docker."""
    print("🚀 Testing Gemini extraction in Docker...")
    
    try:
        # Import directly without backend prefix
        from gemini_extraction_service import GeminiExtractionService
        
        # Find test PDF
        test_paths = [
            "/app/test_data/VTI.pdf",
            "/app/test_pdfs/VTI.pdf"
        ]
        
        test_pdf = None
        for path in test_paths:
            if Path(path).exists():
                test_pdf = path
                break
        
        if not test_pdf:
            print("❌ No test PDF found")
            return False
        
        print(f"📄 Testing with: {Path(test_pdf).name}")
        
        # Initialize service
        service = GeminiExtractionService()
        start_time = time.time()
        
        # Run extraction
        result = await service.extract_fund(test_pdf)
        extraction_time = time.time() - start_time
        
        if result.success:
            print(f"✅ Extraction successful!")
            print(f"   Fund name: {result.fund_data.fund_name}")
            print(f"   Ticker: {result.fund_data.ticker}")
            print(f"   Fund type: {result.fund_data.fund_type}")
            print(f"   Processing time: {extraction_time:.2f}s")
            print(f"   Confidence: {result.confidence_score:.2f}")
            print(f"   Method: {result.method_used}")
            
            if hasattr(result.fund_data, 'nav') and result.fund_data.nav:
                print(f"   NAV: ${result.fund_data.nav}")
            if hasattr(result.fund_data, 'expense_ratio') and result.fund_data.expense_ratio:
                print(f"   Expense ratio: {result.fund_data.expense_ratio}%")
            
            return True
        else:
            print(f"❌ Extraction failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_docling_parsing():
    """Test Docling PDF parsing."""
    print("\n📄 Testing Docling PDF parsing...")
    
    try:
        from docling.document_converter import DocumentConverter
        
        # Find test PDF
        test_paths = [
            "/app/test_data/VTI.pdf",
            "/app/test_pdfs/VTI.pdf"
        ]
        
        test_pdf = None
        for path in test_paths:
            if Path(path).exists():
                test_pdf = path
                break
        
        if not test_pdf:
            print("❌ No test PDF found")
            return False
        
        print(f"📄 Found test PDF: {test_pdf}")
        
        converter = DocumentConverter()
        result = converter.convert(test_pdf)
        
        markdown_content = result.document.export_to_markdown()
        table_count = len(result.document.tables)
        
        print(f"✅ PDF parsed successfully")
        print(f"   Markdown length: {len(markdown_content):,} chars")
        print(f"   Tables found: {table_count}")
        print(f"   Preview: {markdown_content[:200]}...")
        
        return len(markdown_content) > 0
        
    except Exception as e:
        print(f"❌ Docling error: {e}")
        return False

async def main():
    """Run Docker tests."""
    print("🐳 Gemini Extraction Docker Test")
    print("=" * 40)
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🔑 Gemini API key set: {'Yes' if os.getenv('GEMINI_API_KEY') else 'No'}")
    print(f"🐍 Python path: {sys.path[:2]}...")
    print()
    
    # Test Docling parsing
    docling_success = await test_docling_parsing()
    
    # Test full extraction
    extraction_success = await test_gemini_extraction()
    
    print(f"\n📊 Test Results")
    print("=" * 20)
    print(f"{'✅ PASS' if docling_success else '❌ FAIL'} Docling parsing")
    print(f"{'✅ PASS' if extraction_success else '❌ FAIL'} Gemini extraction")
    
    if docling_success and extraction_success:
        print("\n🎉 All tests passed! Gemini extraction is working in Docker!")
        return True
    else:
        print(f"\n⚠️ {sum([docling_success, extraction_success])}/2 tests passed")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
#!/usr/bin/env python3
"""
Test script for Gemini extraction inside Docker container.
"""

import os
import sys
import asyncio
import time
from pathlib import Path

# Add backend paths
sys.path.append('/app')
sys.path.append('/app/backend')

async def test_gemini_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing imports inside Docker...")
    
    try:
        from google import genai
        print("✅ Google GenAI imported")
        
        from docling.document_converter import DocumentConverter
        print("✅ Docling imported")
        
        from backend.gemini_extraction_service import GeminiExtractionService
        print("✅ GeminiExtractionService imported")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_gemini_api():
    """Test Gemini API connectivity."""
    print("\n🤖 Testing Gemini API connectivity...")
    
    try:
        from google import genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not set")
            return False
        
        client = genai.Client(api_key=api_key)
        print("✅ Gemini client created")
        
        # Test simple request
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='Respond with exactly: "Docker test successful"'
        )
        
        result = response.text.strip()
        print(f"✅ API Response: {result}")
        return "successful" in result.lower()
        
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        return False

async def test_docling_parsing():
    """Test Docling PDF parsing with available test files."""
    print("\n📄 Testing Docling PDF parsing...")
    
    try:
        from docling.document_converter import DocumentConverter
        
        # Look for test PDFs in mounted volumes
        test_paths = [
            "/app/test_data/VTI.pdf",
            "/app/test_pdfs/VTI.pdf",
            "/app/data/VTI.pdf"
        ]
        
        test_pdf = None
        for path in test_paths:
            if Path(path).exists():
                test_pdf = path
                break
        
        if not test_pdf:
            print("❌ No test PDF found in Docker")
            print(f"   Searched: {test_paths}")
            return False
        
        print(f"📄 Found test PDF: {test_pdf}")
        
        converter = DocumentConverter()
        result = converter.convert(test_pdf)
        
        markdown_content = result.document.export_to_markdown()
        table_count = len(result.document.tables)
        
        print(f"✅ PDF parsed successfully")
        print(f"   Markdown length: {len(markdown_content):,} chars")
        print(f"   Tables found: {table_count}")
        print(f"   Preview: {markdown_content[:100]}...")
        
        return len(markdown_content) > 0
        
    except Exception as e:
        print(f"❌ Docling error: {e}")
        return False

async def test_full_extraction():
    """Test full Gemini extraction pipeline."""
    print("\n🚀 Testing full extraction pipeline...")
    
    try:
        from backend.gemini_extraction_service import GeminiExtractionService
        
        # Look for test PDF
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
        
        print(f"📄 Testing extraction with: {Path(test_pdf).name}")
        
        service = GeminiExtractionService()
        start_time = time.time()
        
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
        print(f"❌ Full extraction error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("🧪 Gemini Extraction Docker Test")
    print("=" * 40)
    print(f"🐳 Python path: {sys.path[:3]}...")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🔑 Gemini API key set: {'Yes' if os.getenv('GEMINI_API_KEY') else 'No'}")
    print()
    
    tests = [
        ("Imports", test_gemini_imports),
        ("Gemini API", test_gemini_api),
        ("Docling parsing", test_docling_parsing),
        ("Full extraction", test_full_extraction),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 Docker Test Results")
    print("=" * 25)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All Docker tests passed! Gemini extraction is working in container.")
        return True
    elif passed > 0:
        print(f"\n⚠️ Some tests passed. {len(results) - passed} issues to resolve.")
        return False
    else:
        print("\n❌ All tests failed. Check Docker configuration.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
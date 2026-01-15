#!/usr/bin/env python3
"""
Comprehensive Docker test for all PDF files.
"""

import sys
sys.path.insert(0, "/app")
import asyncio
import time
from pathlib import Path

async def test_pdf(pdf_path):
    try:
        from gemini_extraction_service import GeminiExtractionService
        
        service = GeminiExtractionService()
        start_time = time.time()
        
        result = await service.extract_fund(pdf_path)
        extraction_time = time.time() - start_time
        
        return {
            "file": Path(pdf_path).name,
            "success": result.success,
            "time": extraction_time,
            "method": result.method_used,
            "confidence": result.confidence_score,
            "fund_name": result.fund_data.fund_name if result.success else None,
            "ticker": result.fund_data.ticker if result.success else None,
            "fund_type": result.fund_data.fund_type if result.success else None,
            "error": result.error if not result.success else None
        }
    except Exception as e:
        return {
            "file": Path(pdf_path).name,
            "success": False,
            "time": 0,
            "method": None,
            "confidence": 0,
            "fund_name": None,
            "ticker": None,
            "fund_type": None,
            "error": str(e)
        }

async def run_comprehensive_tests():
    test_files = [
        "/app/VTI.pdf",
        "/app/VTV.pdf", 
        "/app/VUG.pdf"
    ]
    
    # Check which files exist
    existing_files = [f for f in test_files if Path(f).exists()]
    print(f"Testing {len(existing_files)} PDF files...\n")
    
    results = []
    for pdf_file in existing_files:
        print(f"📄 Testing {Path(pdf_file).name}...")
        result = await test_pdf(pdf_file)
        results.append(result)
        
        if result["success"]:
            fund_name = result["fund_name"]
            ticker = result["ticker"]
            conf = result["confidence"]
            proc_time = result["time"]
            print(f"   ✅ SUCCESS - {fund_name} ({ticker})")
            print(f"   ⏱️  Time: {proc_time:.1f}s | Confidence: {conf:.2f}")
        else:
            error_msg = result["error"][:60] if result["error"] else "Unknown error"
            print(f"   ❌ FAILED - {error_msg}...")
        print()
    
    return results

if __name__ == "__main__":
    results = asyncio.run(run_comprehensive_tests())

    # Summary
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print("📊 COMPREHENSIVE TEST RESULTS")
    print("=" * 35)
    print(f"Total files tested: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    if successful:
        avg_time = sum(r["time"] for r in successful) / len(successful)
        avg_confidence = sum(r["confidence"] for r in successful) / len(successful)
        print(f"Average processing time: {avg_time:.1f}s")
        print(f"Average confidence: {avg_confidence:.2f}")

    success_rate = 100 * len(successful) / len(results) if results else 0
    print(f"\n🎯 SUCCESS RATE: {len(successful)}/{len(results)} ({success_rate:.0f}%)")
    
    if successful:
        print("\n✅ SUCCESSFUL EXTRACTIONS:")
        for r in successful:
            print(f"   • {r['file']}: {r['fund_name']} ({r['ticker']}) - {r['time']:.1f}s")
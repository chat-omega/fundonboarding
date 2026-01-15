#!/usr/bin/env python3
"""
Test script for the enhanced extraction pipeline with AI-powered classification and routing.
Tests the complete flow: Document Classification → Routing → Extraction
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from document_classifier import DocumentClassifier, check_dependencies as check_classifier_deps
from gemini_multi_fund_extractor import GeminiMultiFundExtractor, check_dependencies as check_multi_deps  
from extraction_service import FundExtractionService
from config import config


class ExtractionPipelineTester:
    """Test suite for the enhanced extraction pipeline."""
    
    def __init__(self):
        self.test_results = {}
        self.classifier = None
        self.multi_extractor = None
        self.service = None
    
    def check_dependencies(self) -> Dict[str, Any]:
        """Check all dependencies for the extraction pipeline."""
        print("🔍 Checking Dependencies")
        print("=" * 50)
        
        # Check individual component dependencies
        classifier_deps = check_classifier_deps()
        multi_deps = check_multi_deps()
        
        # Check overall system
        dependencies = {
            "docling": classifier_deps.get("docling", False),
            "google_genai": classifier_deps.get("google_genai", False),
            "gemini_api_key": bool(os.getenv("GEMINI_API_KEY")),
            "config_valid": config.validate()
        }
        
        # Print dependency status
        for name, available in dependencies.items():
            status = "✓" if available else "✗"
            print(f"  {name}: {status}")
        
        all_available = all(dependencies.values())
        print(f"\nOverall status: {'✓ Ready' if all_available else '✗ Missing dependencies'}")
        
        return dependencies
    
    def initialize_components(self) -> bool:
        """Initialize all extraction components."""
        try:
            print("\n🚀 Initializing Components")
            print("=" * 50)
            
            # Initialize document classifier
            self.classifier = DocumentClassifier()
            print("✓ Document classifier initialized")
            
            # Initialize multi-fund extractor
            self.multi_extractor = GeminiMultiFundExtractor()
            print("✓ Multi-fund extractor initialized")
            
            # Initialize extraction service
            self.service = FundExtractionService()
            print("✓ Extraction service initialized")
            
            return True
            
        except Exception as e:
            print(f"❌ Component initialization failed: {e}")
            return False
    
    async def test_document_classification(self, test_files: List[str]) -> Dict[str, Any]:
        """Test document classification on sample files."""
        print("\n📋 Testing Document Classification")
        print("=" * 50)
        
        results = {}
        
        for file_path in test_files:
            if not Path(file_path).exists():
                print(f"⚠️ Test file not found: {file_path}")
                continue
                
            try:
                start_time = time.time()
                result = await self.classifier.classify_document(file_path)
                classification_time = time.time() - start_time
                
                filename = Path(file_path).name
                results[filename] = {
                    "document_type": result.document_type.value,
                    "confidence": result.confidence,
                    "reasoning": result.reasoning,
                    "fund_count_estimate": result.fund_count_estimate,
                    "fund_names": result.fund_names,
                    "classification_time": classification_time
                }
                
                print(f"📄 {filename}:")
                print(f"   Type: {result.document_type.value}")
                print(f"   Confidence: {result.confidence:.2f}")
                print(f"   Time: {classification_time:.2f}s")
                print(f"   Reasoning: {result.reasoning}")
                
                if result.fund_names:
                    print(f"   Funds found: {', '.join(result.fund_names[:3])}{'...' if len(result.fund_names) > 3 else ''}")
                
            except Exception as e:
                print(f"❌ Classification failed for {file_path}: {e}")
                results[Path(file_path).name] = {"error": str(e)}
        
        return results
    
    async def test_extraction_service(self, test_files: List[str]) -> Dict[str, Any]:
        """Test the unified extraction service."""
        print("\n🔧 Testing Unified Extraction Service")
        print("=" * 50)
        
        results = {}
        
        for file_path in test_files:
            if not Path(file_path).exists():
                print(f"⚠️ Test file not found: {file_path}")
                continue
                
            try:
                filename = Path(file_path).name
                print(f"\n📄 Processing {filename}...")
                
                start_time = time.time()
                result = await self.service.extract_fund(file_path, method='auto')
                extraction_time = time.time() - start_time
                
                results[filename] = {
                    "success": result.success,
                    "method_used": result.method_used,
                    "extraction_time": extraction_time,
                    "document_type": result.document_type,
                    "confidence_score": result.confidence_score,
                    "total_funds_extracted": result.total_funds_extracted
                }
                
                if result.success:
                    print(f"✅ Success!")
                    print(f"   Method: {result.method_used}")
                    print(f"   Document type: {result.document_type}")
                    print(f"   Funds extracted: {result.total_funds_extracted}")
                    print(f"   Time: {extraction_time:.2f}s")
                    print(f"   Confidence: {result.confidence_score:.2f}")
                    
                    # Display fund information
                    if isinstance(result.fund_data, list):
                        print(f"   Fund names:")
                        for i, fund in enumerate(result.fund_data[:5]):  # Show first 5
                            print(f"     {i+1}. {fund.fund_name}")
                        if len(result.fund_data) > 5:
                            print(f"     ... and {len(result.fund_data) - 5} more")
                    else:
                        print(f"   Fund name: {result.fund_data.fund_name}")
                    
                    if result.warnings:
                        print(f"   Warnings: {len(result.warnings)}")
                        for warning in result.warnings[:3]:
                            print(f"     - {warning}")
                
                else:
                    print(f"❌ Failed: {result.error}")
                    results[filename]["error"] = result.error
                    
            except Exception as e:
                print(f"❌ Extraction failed for {file_path}: {e}")
                results[Path(file_path).name] = {"error": str(e)}
        
        return results
    
    def generate_test_report(self, classification_results: Dict, extraction_results: Dict):
        """Generate a comprehensive test report."""
        print("\n📊 Test Report")
        print("=" * 50)
        
        # Classification summary
        total_classifications = len(classification_results)
        successful_classifications = sum(1 for r in classification_results.values() if "error" not in r)
        avg_classification_time = sum(r.get("classification_time", 0) for r in classification_results.values() if "error" not in r) / max(successful_classifications, 1)
        
        print(f"📋 Classification Results:")
        print(f"   Total files: {total_classifications}")
        print(f"   Successful: {successful_classifications}")
        print(f"   Failed: {total_classifications - successful_classifications}")
        print(f"   Average time: {avg_classification_time:.2f}s")
        
        # Document type distribution
        doc_types = {}
        for result in classification_results.values():
            if "document_type" in result:
                doc_type = result["document_type"]
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
        if doc_types:
            print(f"   Document types:")
            for doc_type, count in doc_types.items():
                print(f"     {doc_type}: {count}")
        
        # Extraction summary
        total_extractions = len(extraction_results)
        successful_extractions = sum(1 for r in extraction_results.values() if r.get("success", False))
        avg_extraction_time = sum(r.get("extraction_time", 0) for r in extraction_results.values() if r.get("success", False)) / max(successful_extractions, 1)
        total_funds = sum(r.get("total_funds_extracted", 0) for r in extraction_results.values() if r.get("success", False))
        
        print(f"\n🔧 Extraction Results:")
        print(f"   Total files: {total_extractions}")
        print(f"   Successful: {successful_extractions}")
        print(f"   Failed: {total_extractions - successful_extractions}")
        print(f"   Average time: {avg_extraction_time:.2f}s")
        print(f"   Total funds extracted: {total_funds}")
        
        # Method distribution
        methods = {}
        for result in extraction_results.values():
            if "method_used" in result:
                method = result["method_used"]
                methods[method] = methods.get(method, 0) + 1
        
        if methods:
            print(f"   Methods used:")
            for method, count in methods.items():
                print(f"     {method}: {count}")
        
        # Success rate
        overall_success_rate = (successful_extractions / max(total_extractions, 1)) * 100
        print(f"\n🎯 Overall Success Rate: {overall_success_rate:.1f}%")
        
        # Performance assessment
        if overall_success_rate >= 80:
            print("✅ Performance: Excellent")
        elif overall_success_rate >= 60:
            print("⚠️ Performance: Good - some improvements needed")
        else:
            print("❌ Performance: Needs improvement")
    
    async def run_full_test_suite(self, test_files: List[str]):
        """Run the complete test suite."""
        print("🧪 Enhanced Extraction Pipeline Test Suite")
        print("=" * 70)
        
        # Check dependencies
        deps = self.check_dependencies()
        if not all(deps.values()):
            print("❌ Cannot run tests due to missing dependencies")
            return
        
        # Initialize components
        if not self.initialize_components():
            print("❌ Cannot run tests due to component initialization failure")
            return
        
        # Run tests
        try:
            # Test classification
            classification_results = await self.test_document_classification(test_files)
            
            # Test extraction
            extraction_results = await self.test_extraction_service(test_files)
            
            # Generate report
            self.generate_test_report(classification_results, extraction_results)
            
            print(f"\n🎉 Test suite completed!")
            
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main test function."""
    # Define test files (add paths to actual test PDFs)
    test_files = [
        "/home/ec2-user/fundonboarding/data/VTI.pdf",
        "/home/ec2-user/fundonboarding/data/VTV.pdf", 
        "/home/ec2-user/fundonboarding/data/VUG.pdf",
        "/home/ec2-user/fundonboarding/data/fidelity_fund.pdf"
    ]
    
    # Filter to only existing files
    existing_files = [f for f in test_files if Path(f).exists()]
    
    if not existing_files:
        print("❌ No test files found. Please add some PDF files to test with.")
        print("Expected files:")
        for file in test_files:
            print(f"   {file}")
        return
    
    print(f"📁 Found {len(existing_files)} test files")
    
    # Run test suite
    tester = ExtractionPipelineTester()
    await tester.run_full_test_suite(existing_files)


if __name__ == "__main__":
    asyncio.run(main())
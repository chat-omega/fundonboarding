"""
Comprehensive test framework for fund extraction.
Tests different PDF types and extraction methods.
"""

import asyncio
import sys
from pathlib import Path
import time
from typing import List, Dict

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from backend.extraction_service import FundExtractionService, ExtractionResult
from src.models import FundData


class FundExtractionTester:
    """Test framework for fund extraction."""
    
    def __init__(self):
        self.service = FundExtractionService()
        self.test_documents = [
            "VTI.pdf",  # Vanguard Total Stock Market
            "VTV.pdf",  # Vanguard Value ETF  
            "VUG.pdf",  # Vanguard Growth ETF
            "ivv-ishares-core-s-p-500-etf-fund-fact-sheet-en-us.pdf",  # iShares
            # "iefa-ishares-core-msci-eafe-etf-fund-fact-sheet-en-us.pdf",  # iShares EAFE
        ]
        self.test_methods = ['llamaparse', 'direct_llm', 'auto']
    
    async def test_single_document(self, doc_name: str, method: str) -> Dict:
        """Test extraction on a single document."""
        doc_path = Path(__file__).parent / doc_name
        
        if not doc_path.exists():
            return {
                'document': doc_name,
                'method': method,
                'success': False,
                'error': f'File not found: {doc_path}',
                'fund_data': None,
                'extraction_time': 0.0,
                'validation_score': 0.0
            }
        
        print(f"Testing {doc_name} with {method}...")
        
        try:
            result = await self.service.extract_fund(str(doc_path), method)
            validation_score = self.validate_extraction(result)
            
            return {
                'document': doc_name,
                'method': method,
                'success': result.success,
                'error': result.error,
                'fund_data': result.fund_data.dict() if result.fund_data else None,
                'extraction_time': result.extraction_time,
                'confidence_score': result.confidence_score,
                'validation_score': validation_score
            }
            
        except Exception as e:
            return {
                'document': doc_name,
                'method': method,
                'success': False,
                'error': str(e),
                'fund_data': None,
                'extraction_time': 0.0,
                'validation_score': 0.0
            }
    
    def validate_extraction(self, result: ExtractionResult) -> float:
        """Validate extraction result and return score (0-1)."""
        if not result.success or not result.fund_data:
            return 0.0
        
        fund = result.fund_data
        score = 0.0
        max_score = 10.0
        
        # Required fields
        if fund.fund_name and fund.fund_name != "Unknown Fund":
            score += 3.0  # Fund name is critical
        
        if fund.ticker and len(fund.ticker) >= 2:
            score += 2.0  # Ticker is important
        
        if fund.fund_type:
            score += 1.0
        
        # Financial metrics
        if fund.expense_ratio and fund.expense_ratio > 0:
            score += 1.0
        
        if fund.nav and fund.nav > 0:
            score += 1.0
        
        if fund.net_assets_usd and fund.net_assets_usd > 0:
            score += 1.0
        
        # Performance data
        if fund.one_year_return is not None:
            score += 0.5
        
        # Asset allocation
        if any([fund.equity_pct, fund.fixed_income_pct, fund.money_market_pct]):
            score += 0.5
        
        return min(score / max_score, 1.0)
    
    async def test_all_combinations(self) -> List[Dict]:
        """Test all document/method combinations."""
        results = []
        total_tests = len(self.test_documents) * len(self.test_methods)
        completed = 0
        
        print(f"Running {total_tests} extraction tests...")
        
        for doc in self.test_documents:
            for method in self.test_methods:
                result = await self.test_single_document(doc, method)
                results.append(result)
                completed += 1
                
                # Print progress
                print(f"[{completed}/{total_tests}] {doc} | {method} | " + 
                      f"{'✓' if result['success'] else '✗'} | " +
                      f"Score: {result['validation_score']:.2f}")
        
        return results
    
    def analyze_results(self, results: List[Dict]) -> Dict:
        """Analyze test results and provide summary."""
        total_tests = len(results)
        successful = sum(1 for r in results if r['success'])
        
        # Group by method
        method_stats = {}
        for method in self.test_methods:
            method_results = [r for r in results if r['method'] == method]
            method_stats[method] = {
                'total': len(method_results),
                'successful': sum(1 for r in method_results if r['success']),
                'avg_score': sum(r['validation_score'] for r in method_results) / len(method_results),
                'avg_time': sum(r['extraction_time'] for r in method_results) / len(method_results)
            }
        
        # Group by document
        doc_stats = {}
        for doc in self.test_documents:
            doc_results = [r for r in results if r['document'] == doc]
            successful_extractions = [r for r in doc_results if r['success']]
            
            if successful_extractions:
                best_result = max(successful_extractions, key=lambda x: x['validation_score'])
                doc_stats[doc] = {
                    'extraction_possible': True,
                    'best_method': best_result['method'],
                    'best_score': best_result['validation_score'],
                    'fund_name': best_result['fund_data']['fund_name'] if best_result['fund_data'] else None,
                    'ticker': best_result['fund_data']['ticker'] if best_result['fund_data'] else None
                }
            else:
                doc_stats[doc] = {
                    'extraction_possible': False,
                    'errors': list(set(r['error'] for r in doc_results if r['error']))
                }
        
        return {
            'summary': {
                'total_tests': total_tests,
                'successful': successful,
                'success_rate': successful / total_tests,
                'total_documents': len(self.test_documents),
                'extractable_documents': sum(1 for d in doc_stats.values() if d.get('extraction_possible', False))
            },
            'method_performance': method_stats,
            'document_results': doc_stats,
            'detailed_results': results
        }
    
    def print_summary(self, analysis: Dict):
        """Print formatted test summary."""
        print("\\n" + "="*60)
        print("FUND EXTRACTION TEST SUMMARY")
        print("="*60)
        
        summary = analysis['summary']
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful: {summary['successful']} ({summary['success_rate']:.1%})")
        print(f"Documents: {summary['extractable_documents']}/{summary['total_documents']} extractable")
        
        print("\\n" + "-"*40)
        print("METHOD PERFORMANCE")
        print("-"*40)
        
        for method, stats in analysis['method_performance'].items():
            print(f"{method:12} | {stats['successful']:2}/{stats['total']} | " +
                  f"Avg Score: {stats['avg_score']:.2f} | " +
                  f"Avg Time: {stats['avg_time']:.1f}s")
        
        print("\\n" + "-"*40)
        print("DOCUMENT RESULTS")
        print("-"*40)
        
        for doc, stats in analysis['document_results'].items():
            if stats.get('extraction_possible'):
                print(f"✓ {doc[:30]:30} | {stats['best_method']:10} | {stats['best_score']:.2f}")
                print(f"  → {stats['fund_name']} ({stats['ticker']})")
            else:
                print(f"✗ {doc[:30]:30} | Failed")
                if stats.get('errors'):
                    for error in stats['errors'][:1]:  # Show first error
                        print(f"  → {error[:60]}...")
        
        print("\\n" + "="*60)
    
    async def run_tests(self):
        """Run all tests and print results."""
        print("Starting Fund Extraction Tests...")
        
        results = await self.test_all_combinations()
        analysis = self.analyze_results(results)
        self.print_summary(analysis)
        
        return analysis


async def main():
    """Main test function."""
    tester = FundExtractionTester()
    
    try:
        analysis = await tester.run_tests()
        
        # Save detailed results
        import json
        with open(Path(__file__).parent / "extraction_test_results.json", 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        print("\\nDetailed results saved to: extraction_test_results.json")
        
    except Exception as e:
        print(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
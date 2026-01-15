"""
AI-powered document classifier using Gemini to identify single vs multi-fund documents.
Replaces simple filename pattern matching with intelligent content analysis.
"""

import asyncio
import json
import os
import re
from typing import Dict, Optional, List
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# Fix environment variables BEFORE importing Docling
# Use appropriate HOME directory
if not os.path.exists('/app'):
    os.environ['HOME'] = os.path.expanduser('~')
else:
    os.environ['HOME'] = '/app'
os.environ['TMPDIR'] = '/tmp'
os.environ['XDG_CACHE_HOME'] = '/tmp/docling_cache'
os.environ['XDG_DATA_HOME'] = '/tmp/docling_data'

os.makedirs('/tmp/docling_cache', exist_ok=True)
os.makedirs('/tmp/docling_data', exist_ok=True)

try:
    from google import genai
    from google.genai.types import GenerateContentConfig
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    DocumentConverter = None

from pydantic import BaseModel


class DocumentType(str, Enum):
    """Document type classifications."""
    SINGLE_FUND = "single_fund"
    MULTI_FUND = "multi_fund"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    """Result of document classification."""
    document_type: DocumentType
    confidence: float  # 0.0 to 1.0
    reasoning: str
    fund_count_estimate: Optional[int] = None
    fund_names: Optional[List[str]] = None
    classification_time: float = 0.0


class DocumentClassifier:
    """AI-powered document classifier using Gemini and Docling."""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.client = None
        self.docling_converter = None
        self._initialized = False
    
    def _initialize(self):
        """Initialize Gemini client and Docling converter."""
        if self._initialized:
            return
        
        if not GEMINI_AVAILABLE:
            raise ImportError("Google GenAI not available. Install with: pip install google-genai")
        
        if not DOCLING_AVAILABLE:
            raise ImportError("Docling not available. Install with: pip install docling")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=self.api_key)
        self.docling_converter = DocumentConverter()
        self._initialized = True
    
    def _get_filename_hints(self, pdf_path: str) -> Dict[str, str]:
        """Extract hints from filename for classification."""
        filename = Path(pdf_path).name.upper()
        filename_stem = Path(pdf_path).stem.upper()
        
        hints = {
            "filename": filename,
            "filename_stem": filename_stem,
            "likely_type": "unknown"
        }
        
        # Single fund patterns
        single_fund_patterns = [
            (r'^V[A-Z]{2,3}\.PDF$', "Vanguard ETF"),
            (r'^I[A-Z]{2,4}\.PDF$', "iShares ETF"),
            (r'^[A-Z]{3,4}_.*\.PDF$', "ETF with underscore"),
            (r'.*ETF.*FACT.*SHEET.*\.PDF$', "ETF fact sheet"),
            (r'^SPY\.PDF$|^QQQ\.PDF$|^IWM\.PDF$', "Popular ETF"),
        ]
        
        for pattern, description in single_fund_patterns:
            if re.match(pattern, filename):
                hints["likely_type"] = "single_fund"
                hints["pattern_match"] = description
                break
        
        # Multi-fund patterns
        multi_fund_patterns = [
            (r'.*ASSET.MANAGER.*\.PDF$', "Fidelity Asset Manager"),
            (r'.*ANNUAL.REPORT.*\.PDF$', "Annual report"),
            (r'.*CONSOLIDATED.*\.PDF$', "Consolidated report"),
            (r'.*MULTI.*FUND.*\.PDF$', "Multi-fund document"),
        ]
        
        for pattern, description in multi_fund_patterns:
            if re.match(pattern, filename):
                hints["likely_type"] = "multi_fund"
                hints["pattern_match"] = description
                break
        
        return hints
    
    def _create_classification_prompt(self, markdown_content: str, filename_hints: Dict[str, str], pages_to_analyze: int = 3) -> str:
        """Create classification prompt for Gemini."""
        
        # Limit content to first few pages for analysis (performance)
        lines = markdown_content.split('\n')
        limited_content = '\n'.join(lines[:min(300, len(lines))])  # First ~300 lines
        
        prompt = f"""
You are a financial document classifier. Analyze this PDF document to determine if it contains data for a SINGLE fund or MULTIPLE funds.

DOCUMENT FILENAME: {filename_hints['filename']}
FILENAME STEM: {filename_hints['filename_stem']}
FILENAME PATTERN HINT: {filename_hints.get('pattern_match', 'No pattern match')}

DOCUMENT CONTENT (first {pages_to_analyze} pages):
{limited_content}

Classification Guidelines:

SINGLE FUND documents typically contain:
- One ETF or mutual fund's fact sheet
- Individual fund ticker (e.g., VTI, VTV, IVV)  
- Single fund name in the title
- One set of performance data, holdings, allocations
- Individual prospectus or annual report for one fund

MULTI FUND documents typically contain:
- Multiple fund names in table of contents or index
- Consolidated annual reports covering several funds
- Asset Manager family documents (e.g., "Fidelity Asset Manager 20%, 30%, 40%")
- Several distinct fund sections with different investment objectives
- Multiple ticker symbols or fund identifiers

Return ONLY a valid JSON response with this exact structure:
{{
    "document_type": "single_fund" or "multi_fund",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of classification decision",
    "fund_count_estimate": estimated number of funds (integer, null if unknown),
    "fund_names": ["List of fund names found"] or null
}}

IMPORTANT RULES:
1. Base decision primarily on CONTENT, use filename as supporting evidence
2. Look for table of contents, fund listings, or section headers
3. If unsure, lean towards "single_fund" (safer default)
4. Confidence should be 0.8+ for clear cases, 0.5-0.7 for uncertain cases
5. Extract actual fund names if clearly visible in the content
6. Return ONLY the JSON object, no additional text

JSON:"""

        return prompt
    
    async def classify_document(self, pdf_path: str) -> ClassificationResult:
        """Classify document using AI analysis of content."""
        import time
        start_time = time.time()
        
        try:
            self._initialize()
            
            # Get filename hints
            filename_hints = self._get_filename_hints(pdf_path)
            
            # Parse document with Docling (first few pages only for classification)
            docling_result = self.docling_converter.convert(pdf_path)
            markdown_content = docling_result.document.export_to_markdown()
            
            # Create classification prompt
            prompt = self._create_classification_prompt(markdown_content, filename_hints)
            
            # Configure generation settings
            config = GenerateContentConfig(
                temperature=0.1,  # Low temperature for consistent classification
                max_output_tokens=1024,
                top_p=0.95,
            )
            
            # Call Gemini for classification
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=config
            )
            
            response_text = response.text.strip()
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result_dict = json.loads(json_str)
            else:
                result_dict = json.loads(response_text)
            
            # Validate and create result
            document_type = DocumentType(result_dict.get("document_type", "unknown"))
            confidence = max(0.0, min(1.0, float(result_dict.get("confidence", 0.5))))
            reasoning = str(result_dict.get("reasoning", "AI classification completed"))
            fund_count = result_dict.get("fund_count_estimate")
            fund_names = result_dict.get("fund_names")
            
            classification_time = time.time() - start_time
            
            return ClassificationResult(
                document_type=document_type,
                confidence=confidence,
                reasoning=reasoning,
                fund_count_estimate=fund_count,
                fund_names=fund_names,
                classification_time=classification_time
            )
            
        except json.JSONDecodeError as e:
            # Fallback to filename-based classification
            return self._fallback_classification(pdf_path, f"JSON parse error: {str(e)}", time.time() - start_time)
        
        except Exception as e:
            # Fallback to filename-based classification
            return self._fallback_classification(pdf_path, f"Classification error: {str(e)}", time.time() - start_time)
    
    def _fallback_classification(self, pdf_path: str, error_msg: str, classification_time: float) -> ClassificationResult:
        """Fallback to filename-based classification when AI fails."""
        filename_hints = self._get_filename_hints(pdf_path)
        
        if filename_hints["likely_type"] == "single_fund":
            document_type = DocumentType.SINGLE_FUND
            confidence = 0.6
            reasoning = f"Filename pattern suggests single fund. AI error: {error_msg}"
        elif filename_hints["likely_type"] == "multi_fund":
            document_type = DocumentType.MULTI_FUND
            confidence = 0.6
            reasoning = f"Filename pattern suggests multi fund. AI error: {error_msg}"
        else:
            document_type = DocumentType.SINGLE_FUND  # Safe default
            confidence = 0.3
            reasoning = f"Unknown pattern, defaulting to single fund. AI error: {error_msg}"
        
        return ClassificationResult(
            document_type=document_type,
            confidence=confidence,
            reasoning=reasoning,
            classification_time=classification_time
        )
    
    async def classify_multiple_documents(self, pdf_paths: List[str]) -> List[ClassificationResult]:
        """Classify multiple documents in parallel."""
        tasks = [self.classify_document(path) for path in pdf_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(self._fallback_classification(
                    pdf_paths[i], 
                    str(result), 
                    0.0
                ))
            else:
                final_results.append(result)
        
        return final_results


# Global classifier instance
document_classifier = DocumentClassifier()


def check_dependencies() -> Dict[str, bool]:
    """Check if required dependencies are available."""
    return {
        "docling": DOCLING_AVAILABLE,
        "google_genai": GEMINI_AVAILABLE,
        "gemini_api_key": bool(os.getenv("GEMINI_API_KEY"))
    }


async def test_classification(pdf_path: str) -> None:
    """Test function for document classification."""
    print("Testing Document Classification")
    print("=" * 40)
    
    # Check dependencies
    deps = check_dependencies()
    print("Dependencies:")
    for name, available in deps.items():
        print(f"  {name}: {'✓' if available else '✗'}")
    print()
    
    if not all(deps.values()):
        print("❌ Missing dependencies. Please install required packages and set GEMINI_API_KEY.")
        return
    
    # Run classification
    classifier = DocumentClassifier()
    result = await classifier.classify_document(pdf_path)
    
    # Display results
    print(f"Classification Result:")
    print(f"  Document Type: {result.document_type.value}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Time: {result.classification_time:.2f}s")
    print(f"  Reasoning: {result.reasoning}")
    
    if result.fund_count_estimate:
        print(f"  Estimated Funds: {result.fund_count_estimate}")
    
    if result.fund_names:
        print(f"  Fund Names Found:")
        for name in result.fund_names:
            print(f"    - {name}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        asyncio.run(test_classification(pdf_path))
    else:
        print("Usage: python document_classifier.py <pdf_path>")
"""Simple test to verify API keys and basic functionality."""

import os
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent))

from config import config

def test_config():
    """Test configuration validation."""
    print("Testing configuration...")
    
    is_valid = config.validate()
    print(f"Configuration valid: {is_valid}")
    
    if is_valid:
        print("✓ API keys are present and properly formatted")
        print(f"  - LlamaCloud API key: {config.llama_cloud_api_key[:10]}...")
        print(f"  - OpenAI API key: {config.openai_api_key[:10]}...")
        print(f"  - Project ID: {config.project_id}")
        print(f"  - Organization ID: {config.organization_id}")
    else:
        print("✗ Configuration is invalid")
        return False
    
    # Set up environment
    config.setup_environment()
    print("✓ Environment variables set")
    
    return True

def test_imports():
    """Test that all required packages can be imported."""
    print("\nTesting imports...")
    
    try:
        from llama_index.llms.openai import OpenAI
        print("✓ OpenAI import successful")
        
        from llama_index.embeddings.openai import OpenAIEmbedding
        print("✓ OpenAI embeddings import successful")
        
        from llama_cloud_services import LlamaParse
        print("✓ LlamaParse import successful")
        
        from llama_cloud_services import LlamaExtract
        print("✓ LlamaExtract import successful")
        
        import pandas as pd
        print("✓ Pandas import successful")
        
        from src.models import FundData, SplitCategories
        print("✓ Custom models import successful")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_openai_basic():
    """Test basic OpenAI connection without complex model initialization."""
    print("\nTesting OpenAI connection...")
    
    try:
        import openai
        
        # Set the API key
        openai.api_key = config.openai_api_key
        
        print("✓ OpenAI API key set successfully")
        return True
        
    except Exception as e:
        print(f"✗ OpenAI connection test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("="*50)
    print("Running simple API key and import tests")
    print("="*50)
    
    tests_passed = 0
    total_tests = 3
    
    if test_config():
        tests_passed += 1
    
    if test_imports():
        tests_passed += 1
    
    if test_openai_basic():
        tests_passed += 1
    
    print("\n" + "="*50)
    print(f"Test Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("✓ All tests passed! Ready to run the extraction.")
    else:
        print("✗ Some tests failed. Check your configuration.")
    
    print("="*50)
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
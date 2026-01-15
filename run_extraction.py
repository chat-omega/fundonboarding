"""Simple script to run the fund extraction."""

import asyncio
import sys
from pathlib import Path
import pandas as pd

from main import main


def run_with_error_handling():
    """Run the extraction with proper error handling."""
    try:
        print("Starting Fidelity Fund Extraction...")
        print("="*60)
        
        # Run the main extraction
        result_df = asyncio.run(main())
        
        if result_df is not None:
            print("\n" + "="*60)
            print("EXTRACTION SUCCESSFUL!")
            print("="*60)
            print(f"Extracted data for {len(result_df)} funds")
            print("\nDataFrame Info:")
            print(result_df.info())
            print("\nFirst few rows:")
            print(result_df.head())
            
            return True
        else:
            print("\nExtraction failed - no results returned")
            return False
            
    except KeyboardInterrupt:
        print("\nExtraction cancelled by user")
        return False
        
    except Exception as e:
        print(f"\nExtraction failed with error: {e}")
        print("\nFull error traceback:")
        import traceback
        traceback.print_exc()
        
        print("\nTroubleshooting tips:")
        print("1. Check your API keys in .env file")
        print("2. Ensure you have internet connection")
        print("3. Verify LlamaCloud project/organization IDs")
        print("4. Check if the PDF URL is accessible")
        
        return False


if __name__ == "__main__":
    success = run_with_error_handling()
    sys.exit(0 if success else 1)
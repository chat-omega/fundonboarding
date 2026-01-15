"""Test LlamaParse functionality with the downloaded PDF."""

import os
import sys
import asyncio
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent))

from config import config
from llama_cloud_services import LlamaParse

async def test_llamaparse():
    """Test LlamaParse with the downloaded PDF."""
    print("Testing LlamaParse...")
    
    # Set up environment
    config.setup_environment()
    
    try:
        # Initialize LlamaParse (without project/org IDs to use defaults)
        parser = LlamaParse(
            premium_mode=True,
            result_type="markdown",
        )
        print("✓ LlamaParse initialized successfully")
        
        # Parse the PDF (just first few pages for testing)
        pdf_path = "./data/asset_manager_fund_analysis/fidelity_fund.pdf"
        
        if not os.path.exists(pdf_path):
            print(f"✗ PDF not found at {pdf_path}")
            return False
        
        print(f"Parsing PDF: {pdf_path}")
        print("This may take a few minutes...")
        
        result = await parser.aparse(pdf_path)
        print("✓ PDF parsing completed")
        
        # Get markdown nodes
        markdown_nodes = await result.aget_markdown_nodes(split_by_page=True)
        print(f"✓ Generated {len(markdown_nodes)} page nodes")
        
        # Show some sample content from the first few pages
        if len(markdown_nodes) > 0:
            print("\n--- Sample content from first page ---")
            first_page = markdown_nodes[0]
            content = first_page.get_content()
            print(content[:500] + "..." if len(content) > 500 else content)
        
        if len(markdown_nodes) > 1:
            print("\n--- Sample content from second page ---")
            second_page = markdown_nodes[1]
            content = second_page.get_content()
            print(content[:500] + "..." if len(content) > 500 else content)
        
        print(f"\n✓ LlamaParse test successful!")
        print(f"  - Parsed {len(markdown_nodes)} pages")
        print(f"  - Ready for fund extraction")
        
        return True
        
    except Exception as e:
        print(f"✗ LlamaParse test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the LlamaParse test."""
    print("="*60)
    print("Testing LlamaParse with Fidelity Fund PDF")
    print("="*60)
    
    success = await test_llamaparse()
    
    print("\n" + "="*60)
    if success:
        print("✓ LlamaParse test PASSED - Ready for extraction!")
    else:
        print("✗ LlamaParse test FAILED - Check configuration")
    print("="*60)
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
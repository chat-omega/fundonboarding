"""Main script to run Fidelity fund extraction."""

import asyncio
import os
import nest_asyncio
import pandas as pd
from pathlib import Path

from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings
from llama_cloud_services import LlamaParse
# from llama_index.experimental.query_engine import PandasQueryEngine

from config import config
from src.fund_extractor import FidelityFundExtraction, setup_extract_agent


# Enable nested asyncio (useful for Jupyter notebooks)
nest_asyncio.apply()

# Fund extraction configuration
FIDELITY_SPLIT_DESCRIPTION = "Find and split by the main funds in this document, should be listed in the first few pages"
FIDELITY_SPLIT_RULES = """
- You must split by the name of the fund
- Each fund will have a list of tables underneath it, like schedule of investments, financial statements
- Each fund usually has schedule of investments right underneath it 
- Do not tag the cover page/table of contents
"""
FIDELITY_SPLIT_KEY = "fidelity_asset_manager"

PDF_URL = "https://www.dropbox.com/scl/fi/bhrtivs7b2gz3yhrr4t4s/fidelity_fund.pdf?rlkey=ha2loufvuer1c07u47k68hgji&st=ev66x31t&dl=1"
PDF_PATH = "./data/asset_manager_fund_analysis/fidelity_fund.pdf"


async def download_pdf():
    """Download the PDF if it doesn't exist."""
    pdf_path = Path(PDF_PATH)
    if pdf_path.exists():
        print(f"PDF already exists at {PDF_PATH}")
        return str(pdf_path.absolute())
    
    print("Downloading PDF...")
    try:
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        
        import subprocess
        result = subprocess.run(
            ["wget", PDF_URL, "-O", PDF_PATH],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print(f"PDF downloaded to {PDF_PATH}")
            
            # Verify the file was actually created and has content
            if not pdf_path.exists() or pdf_path.stat().st_size == 0:
                raise Exception("Downloaded file is empty or does not exist")
                
        else:
            raise Exception(f"wget failed: {result.stderr}")
        
    except subprocess.TimeoutExpired:
        raise Exception("PDF download timed out after 5 minutes")
    except Exception as e:
        raise Exception(f"Failed to download PDF: {str(e)}")
    
    return str(pdf_path.absolute())


def setup_models():
    """Set up LLM and embedding models."""
    try:
        embed_model = OpenAIEmbedding(model_name="text-embedding-3-small")
        llm = OpenAI(
            model="gpt-4o",
            default_headers={},
            logprobs=False
        )
        Settings.llm = llm
        Settings.embed_model = embed_model
        print("✓ Models initialized successfully")
        return llm
    except Exception as e:
        raise Exception(f"Failed to initialize models: {str(e)}. Check your OpenAI API key.")


def setup_parser(project_id: str = None, organization_id: str = None):
    """Set up LlamaParse."""
    try:
        kwargs = {
            "premium_mode": True,
            "result_type": "markdown",
        }
        if project_id:
            kwargs["project_id"] = project_id
        if organization_id:
            kwargs["organization_id"] = organization_id
            
        parser = LlamaParse(**kwargs)
        print("✓ LlamaParse initialized successfully")
        return parser
    except Exception as e:
        raise Exception(f"Failed to initialize LlamaParse: {str(e)}. Check your LlamaCloud API key and project settings.")


async def run_extraction(file_path: str):
    """Run the complete fund extraction workflow."""
    print("Setting up models and services...")
    
    try:
        # Set up models
        llm = setup_models()
        
        # Set up LlamaParse
        parser = setup_parser(config.project_id, config.organization_id)
        
        # Set up LlamaExtract agent
        extract_agent = setup_extract_agent(config.project_id, config.organization_id)
        
        # Create workflow
        workflow = FidelityFundExtraction(
            parser=parser,
            extract_agent=extract_agent,
            split_description=FIDELITY_SPLIT_DESCRIPTION,
            split_rules=FIDELITY_SPLIT_RULES,
            split_key=FIDELITY_SPLIT_KEY,
            llm=llm,
            verbose=True,
            timeout=None
        )
        
        print("Starting extraction workflow...")
        result = await workflow.run(file_path=file_path)
        
        if result is None or "all_fund_data_df" not in result:
            raise Exception("Workflow completed but returned no results")
        
        return result
        
    except Exception as e:
        print(f"Error during extraction workflow: {str(e)}")
        raise


def analyze_results(result_df):
    """Perform basic analysis on the results."""
    print("\n" + "="*50)
    print("ANALYSIS RESULTS")
    print("="*50)
    
    print(f"Number of funds extracted: {len(result_df)}")
    print("\nFund names:")
    for name in result_df['fund_name']:
        print(f"  - {name}")
    
    # Calculate return per unit of risk (equity allocation)
    if 'one_year_return' in result_df.columns and 'equity_pct' in result_df.columns:
        result_df["return_per_risk"] = (
            result_df["one_year_return"] / result_df["equity_pct"]
        )
        print(f"\nReturn per risk ratios:")
        for _, row in result_df.iterrows():
            if pd.notna(row['return_per_risk']):
                print(f"  {row['fund_name']}: {row['return_per_risk']:.3f}")
    
    # How far do actual allocations drift from targets?
    if 'equity_pct' in result_df.columns and 'target_equity_pct' in result_df.columns:
        result_df["drift"] = (
            result_df["equity_pct"] - result_df["target_equity_pct"]
        )
        print(f"\nEquity allocation drift from target:")
        for _, row in result_df.iterrows():
            if pd.notna(row['drift']):
                print(f"  {row['fund_name']}: {row['drift']:.1f}% drift")
    
    return result_df


def save_results(result_df, output_path="fund_extraction_results.csv"):
    """Save results to CSV."""
    result_df.to_csv(output_path, index=False)
    print(f"\nResults saved to {output_path}")


async def main():
    """Main execution function."""
    try:
        # Validate configuration
        if not config.validate():
            print("\nPlease update your .env file with valid API keys and run again.")
            return
        
        # Set up environment
        config.setup_environment()
        
        # Download PDF if needed
        pdf_path = await download_pdf()
        
        # Run extraction
        result = await run_extraction(pdf_path)
        
        # Get results
        all_fund_data_df = result["all_fund_data_df"]
        
        # Analyze results
        analyzed_df = analyze_results(all_fund_data_df)
        
        # Save results
        save_results(analyzed_df)
        
        # Analysis complete
        print("\n" + "="*50)
        print("Analysis complete - query engine not available in this version")
        
        # Show sample results instead
        print("\nSample Results:")
        if len(analyzed_df) > 0:
            print(analyzed_df[['fund_name', 'equity_pct', 'target_equity_pct', 'drift']].head())
        
        print("\nExtraction complete! You can now use the query engine for further analysis.")
        return analyzed_df
        
    except Exception as e:
        print(f"Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    # For direct execution
    result_df = asyncio.run(main())
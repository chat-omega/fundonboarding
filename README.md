# Fidelity Fund Extraction Tool

This tool extracts structured data from Fidelity Asset Manager fund documents using LlamaCloud's LlamaParse and LlamaExtract services.

## Features

- **Automated PDF Processing**: Downloads and parses fund documents
- **Smart Document Splitting**: Automatically identifies different funds in the document
- **Structured Data Extraction**: Extracts key fund metrics (NAV, expense ratios, allocations, etc.)
- **Analysis & Export**: Provides analysis tools and CSV export functionality
- **Error Handling**: Comprehensive error handling and validation

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your actual keys:
```
LLAMA_CLOUD_API_KEY=llx-your-actual-key
OPENAI_API_KEY=sk-proj-your-actual-key
PROJECT_ID=your-project-id
ORGANIZATION_ID=your-organization-id
```

### 3. Get API Keys

- **LlamaCloud API Key**: Sign up at [cloud.llamaindex.ai](https://cloud.llamaindex.ai)
- **OpenAI API Key**: Get from [platform.openai.com](https://platform.openai.com)

## Usage

### Quick Start

Run the complete extraction:
```bash
python run_extraction.py
```

### Step by Step

1. **Test your setup**:
```bash
python tests/test_extraction.py
```

2. **Run extraction**:
```bash
python main.py
```

### Using as a Module

```python
import asyncio
from main import main

# Run extraction
result_df = asyncio.run(main())
print(result_df.head())
```

## Output

The tool generates:
- `fund_extraction_results.csv` - Structured fund data
- Console output with analysis results
- Interactive query engine for further analysis

## Project Structure

```
fundonboarding/
├── src/
│   ├── models.py           # Pydantic data models
│   ├── split_detector.py   # Document splitting logic
│   └── fund_extractor.py   # Main extraction workflow
├── tests/
│   └── test_extraction.py  # Test suite
├── data/                   # Downloaded PDFs
├── config.py              # Configuration management
├── main.py                # Main extraction script
├── run_extraction.py      # Simple runner with error handling
└── requirements.txt       # Python dependencies
```

## Key Components

### 1. Document Splitting
- Automatically identifies fund sections in the document
- Uses LLM to find category boundaries
- Splits document by fund for targeted extraction

### 2. Data Extraction
- Extracts 20+ fund metrics per fund
- Handles multiple fund types and share classes
- Validates extracted data structure

### 3. Analysis
- Calculates return-per-risk ratios
- Analyzes allocation drift from targets
- Provides interactive query capabilities

## Extracted Data Fields

- **Identifiers**: Fund name, target allocation, report date
- **Asset Allocation**: Equity, fixed income, money market percentages
- **Performance**: NAV, returns, expense ratios, management fees
- **Risk Metrics**: Futures positions, portfolio turnover
- **Fund Flows**: Investment income, distributions, asset changes

## Troubleshooting

### Common Issues

1. **API Key Errors**
   - Verify keys are correct in `.env`
   - Check API key permissions and quotas

2. **PDF Download Fails**
   - Check internet connection
   - Verify PDF URL is accessible
   - Try downloading manually first

3. **Extraction Fails**
   - Check LlamaCloud project/organization IDs
   - Verify sufficient API credits
   - Review error logs for specific issues

### Error Messages

- `Configuration invalid`: Update `.env` with real API keys
- `Failed to download PDF`: Check network and URL
- `Failed to initialize models`: Check OpenAI API key
- `Workflow returned no results`: Check document format or extraction settings

## Development

### Running Tests

```bash
# Basic tests (no API calls)
python tests/test_extraction.py

# Full test with API calls (requires valid keys)
python tests/test_extraction.py --full
```

### Customizing Extraction

Modify these variables in `main.py`:
- `FIDELITY_SPLIT_DESCRIPTION`: How to find fund categories
- `FIDELITY_SPLIT_RULES`: Rules for identifying fund sections
- `FIDELITY_SPLIT_KEY`: Naming pattern for extracted funds

### Adding New Data Fields

1. Update the `FundData` model in `src/models.py`
2. The LLM will automatically extract new fields based on field descriptions

## License

This project is for educational/testing purposes. Ensure compliance with API terms of service.
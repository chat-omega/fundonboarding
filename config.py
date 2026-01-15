"""Configuration management for the Fidelity Fund Extractor."""

import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for API keys and settings."""
    
    def __init__(self):
        self.llama_cloud_api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.project_id = os.getenv("PROJECT_ID")
        self.organization_id = os.getenv("ORGANIZATION_ID")
        
        # Gemini API configuration
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        # Document classification settings
        self.document_classification_model = os.getenv("DOCUMENT_CLASSIFICATION_MODEL", "gemini-2.5-flash")
        self.enable_ai_classification = os.getenv("ENABLE_AI_CLASSIFICATION", "true").lower() == "true"
        
        # Multi-fund extraction settings
        self.multi_fund_extraction_enabled = os.getenv("MULTI_FUND_EXTRACTION_ENABLED", "true").lower() == "true"
        self.max_funds_per_document = int(os.getenv("MAX_FUNDS_PER_DOCUMENT", "20"))
        
        # Extraction method selection
        self.extraction_method = os.getenv("EXTRACTION_METHOD", "auto")  # auto, legacy, gemini, ai_powered
        
    def validate(self) -> bool:
        """Validate that all required configuration is present."""
        missing = []
        warnings = []
        
        # Check extraction method and required APIs
        if self.extraction_method in ["auto", "legacy"]:
            # Legacy extraction requires LlamaCloud and OpenAI
            required_fields = [
                ("LLAMA_CLOUD_API_KEY", self.llama_cloud_api_key),
                ("OPENAI_API_KEY", self.openai_api_key),
            ]
            
            for field_name, value in required_fields:
                if not value or value in ["llx-...", "sk-proj-..."]:
                    missing.append(field_name)
        
        if self.extraction_method in ["auto", "gemini", "ai_powered"]:
            # AI-powered extraction requires Gemini API key
            if not self.gemini_api_key or self.gemini_api_key.startswith("AIza..."):
                if self.extraction_method in ["gemini", "ai_powered"]:
                    missing.append("GEMINI_API_KEY")
                else:
                    warnings.append("GEMINI_API_KEY not set - will use legacy extraction methods")
        
        # Validate AI classification settings
        if self.enable_ai_classification and not self.gemini_api_key:
            warnings.append("AI classification enabled but GEMINI_API_KEY not set - will use filename patterns")
        
        # Validate multi-fund settings
        if self.multi_fund_extraction_enabled and not self.gemini_api_key:
            warnings.append("Multi-fund extraction enabled but GEMINI_API_KEY not set - multi-fund documents may fail")
        
        if self.max_funds_per_document < 1 or self.max_funds_per_document > 100:
            warnings.append(f"MAX_FUNDS_PER_DOCUMENT ({self.max_funds_per_document}) is unusual - recommended range: 1-100")
        
        if missing:
            print(f"❌ Missing or invalid configuration: {', '.join(missing)}")
            print("Please update your .env file with actual API keys")
            return False
        
        # Display warnings
        for warning in warnings:
            print(f"⚠️ Warning: {warning}")
        
        # Display configuration summary
        print(f"✓ Extraction method: {self.extraction_method}")
        print(f"✓ AI classification: {'enabled' if self.enable_ai_classification else 'disabled'}")
        print(f"✓ Multi-fund extraction: {'enabled' if self.multi_fund_extraction_enabled else 'disabled'}")
        
        # Warn about missing project IDs but don't fail
        if not self.project_id and self.extraction_method in ["auto", "legacy"]:
            print("📝 Note: PROJECT_ID not set, using LlamaCloud defaults")
        if not self.organization_id and self.extraction_method in ["auto", "legacy"]:
            print("📝 Note: ORGANIZATION_ID not set, using LlamaCloud defaults")
        
        return True
    
    def setup_environment(self):
        """Set up environment variables for the APIs."""
        if self.llama_cloud_api_key:
            os.environ["LLAMA_CLOUD_API_KEY"] = self.llama_cloud_api_key
        if self.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.openai_api_key
        if self.gemini_api_key:
            os.environ["GEMINI_API_KEY"] = self.gemini_api_key

# Global config instance
config = Config()
#!/usr/bin/env python3
"""Test script that mimics the backend extraction flow."""

import sys
import os
import asyncio

# Add the backend directory to the Python path like the main app does
sys.path.append('./backend')
sys.path.append('.')

# Set environment variables exactly like main.py
if not os.path.exists('/app'):
    os.environ['HOME'] = os.path.expanduser('~')
else:
    os.environ['HOME'] = '/app'

os.environ['TMPDIR'] = '/tmp'
os.environ['XDG_CACHE_HOME'] = '/tmp/docling_cache'
os.environ['XDG_DATA_HOME'] = '/tmp/docling_data'

# Ensure temp directories exist
os.makedirs('/tmp/docling_cache', exist_ok=True)
os.makedirs('/tmp/docling_data', exist_ok=True)

print("Testing backend extraction flow...")
print(f"HOME: {os.environ.get('HOME')}")
print(f"PYTHONPATH includes: {sys.path[:3]}")

try:
    # Import exactly like the backend does
    from config import config
    print("✅ Config imported")
    
    # Import the agent like main.py does
    from agent import FundExtractionAgent
    print("✅ FundExtractionAgent imported")
    
    # Test the extraction flow
    async def test_extraction():
        print("Creating FundExtractionAgent...")
        agent = FundExtractionAgent()
        
        print("Starting PDF extraction...")
        pdf_path = "./tests/VTI.pdf"
        
        event_count = 0
        async for event in agent.extract_from_pdf(pdf_path, "Extract fund data"):
            event_count += 1
            print(f"  Event {event_count}: {event.type.value}")
            
            if event.type.value == "error":
                print(f"    ❌ Error: {event.data}")
                break
            elif event.type.value == "results":
                print(f"    ✅ Results: {event.data}")
                break
                
            # Stop after 20 events to avoid infinite loop
            if event_count >= 20:
                print("    ⚠️ Stopping after 20 events")
                break
    
    # Run the async test
    asyncio.run(test_extraction())
    
except Exception as e:
    print(f"❌ Error in backend flow: {e}")
    import traceback
    traceback.print_exc()
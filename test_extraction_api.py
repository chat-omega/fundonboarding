#!/usr/bin/env python3
"""Test script for the Fund Extraction API."""

import requests
import json
import time
import os
from pathlib import Path


def test_health():
    """Test the health endpoint."""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get("http://localhost:8002/health", timeout=5)
        print(f"✅ Health check: {response.status_code} - {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_upload(pdf_path):
    """Test file upload."""
    print(f"📤 Testing upload with {pdf_path}...")
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
            response = requests.post("http://localhost:8002/upload", files=files, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Upload successful: {result['filename']} ({result['size']} bytes)")
            print(f"   File path: {result['file_path']}")
            return result['file_path']
        else:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None


def test_extraction_streaming(pdf_path):
    """Test streaming extraction endpoint."""
    print(f"🔄 Testing streaming extraction with {pdf_path}...")
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
            
            # Stream the response
            response = requests.post(
                "http://localhost:8002/fund-extraction-agent",
                files=files,
                stream=True,
                timeout=120
            )
            
            if response.status_code == 200:
                print("✅ Streaming extraction started...")
                event_count = 0
                
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            event_count += 1
                            try:
                                event_data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                                event_type = event_data.get('type', 'unknown')
                                print(f"  📨 Event {event_count}: {event_type}")
                                
                                # Print interesting event details
                                if event_type == 'status':
                                    data = event_data.get('data', {})
                                    print(f"     Status: {data.get('stage', 'unknown')} - {data.get('message', '')}")
                                elif event_type == 'fund_extracted':
                                    data = event_data.get('data', {})
                                    fund_name = data.get('fund_name', 'Unknown Fund')
                                    print(f"     Fund extracted: {fund_name}")
                                elif event_type == 'results':
                                    data = event_data.get('data', {})
                                    fund_count = data.get('total_funds', 0)
                                    print(f"     ✅ Extraction completed: {fund_count} funds found")
                                elif event_type == 'error':
                                    data = event_data.get('data', {})
                                    print(f"     ❌ Error: {data.get('message', 'Unknown error')}")
                                    
                            except json.JSONDecodeError as e:
                                print(f"     ⚠️ Failed to parse event: {line_str}")
                
                print(f"🎉 Streaming completed with {event_count} events")
                return True
            else:
                print(f"❌ Streaming extraction failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Streaming extraction error: {e}")
        return False


def test_mock_extraction():
    """Test mock extraction endpoint."""
    print("🎭 Testing mock extraction...")
    try:
        payload = {
            "file_path": "/fake/path/test.pdf",
            "message": "Extract fund data from this PDF"
        }
        
        response = requests.post(
            "http://localhost:8002/fund-extraction-agent-mock",
            json=payload,
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Mock extraction started...")
            event_count = 0
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        event_count += 1
                        try:
                            event_data = json.loads(line_str[6:])
                            event_type = event_data.get('type', 'unknown')
                            print(f"  📨 Mock Event {event_count}: {event_type}")
                        except json.JSONDecodeError:
                            pass
            
            print(f"🎉 Mock extraction completed with {event_count} events")
            return True
        else:
            print(f"❌ Mock extraction failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Mock extraction error: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Starting Fund Extraction API Tests")
    print("=" * 50)
    
    # Test 1: Health check
    if not test_health():
        print("❌ Health check failed, stopping tests")
        return
    
    print()
    
    # Test 2: Mock extraction (doesn't need files)
    test_mock_extraction()
    
    print()
    
    # Test 3: Find a sample PDF file
    sample_pdfs = [
        "./tests/VTI.pdf",
        "./tests/VTV.pdf", 
        "./tests/VUG.pdf",
        "./data/VTI.pdf",
        "./data/fidelity_fund.pdf"
    ]
    
    pdf_path = None
    for path in sample_pdfs:
        if os.path.exists(path):
            pdf_path = path
            print(f"📄 Found sample PDF: {pdf_path}")
            break
    
    if not pdf_path:
        print("❌ No sample PDF found for testing")
        return
    
    # Test 4: Upload
    uploaded_path = test_upload(pdf_path)
    
    print()
    
    # Test 5: Streaming extraction
    test_extraction_streaming(pdf_path)
    
    print()
    print("🏁 Tests completed!")


if __name__ == "__main__":
    main()
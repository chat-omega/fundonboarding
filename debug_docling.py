#!/usr/bin/env python3
"""Debug script to isolate docling issue."""

import os
import sys
import traceback

# Set environment variables like the main app
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

print("Environment variables:")
print(f"HOME: {os.environ.get('HOME')}")
print(f"XDG_CACHE_HOME: {os.environ.get('XDG_CACHE_HOME')}")
print(f"XDG_DATA_HOME: {os.environ.get('XDG_DATA_HOME')}")
print(f"TMPDIR: {os.environ.get('TMPDIR')}")
print()

try:
    print("Importing docling...")
    from docling.document_converter import DocumentConverter
    print("✅ Docling imported successfully")
    
    print("Creating DocumentConverter...")
    converter = DocumentConverter()
    print("✅ DocumentConverter created successfully")
    
    print("Checking if test PDF exists...")
    test_pdf = "./tests/VTI.pdf"
    if os.path.exists(test_pdf):
        print(f"✅ Found test PDF: {test_pdf}")
        
        print("Starting document conversion...")
        result = converter.convert(test_pdf)
        print("✅ Document converted successfully!")
        print(f"Result type: {type(result)}")
        
    else:
        print(f"❌ Test PDF not found: {test_pdf}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    print("\n" + "="*50)
    
    # Check if it's specifically a permission error
    if "Permission denied" in str(e) and "/app" in str(e):
        print("\n🔍 Investigating /app permission issue...")
        
        # Check what files/directories might be causing issues
        potential_paths = [
            '/app',
            '/app/models',
            '/app/.cache',
            '/app/.local',
            '/app/.config'
        ]
        
        for path in potential_paths:
            try:
                exists = os.path.exists(path)
                if exists:
                    readable = os.access(path, os.R_OK)
                    writable = os.access(path, os.W_OK)
                    print(f"  {path}: EXISTS, readable={readable}, writable={writable}")
                else:
                    print(f"  {path}: DOES NOT EXIST")
            except Exception as check_err:
                print(f"  {path}: Error checking - {check_err}")
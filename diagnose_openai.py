#!/usr/bin/env python3
"""
OpenAI Library Diagnostic Tool
==============================
Check OpenAI library version and available attributes
"""

try:
    import openai
    print(f"✅ OpenAI library imported successfully")
    print(f"OpenAI version: {openai.__version__}")
    print(f"OpenAI module file: {openai.__file__}")
    print()
    
    print("Available attributes in openai module:")
    attrs = [attr for attr in dir(openai) if not attr.startswith('_')]
    for attr in sorted(attrs):
        print(f"  - {attr}")
    print()
    
    # Check for error module
    if hasattr(openai, 'error'):
        print("✅ openai.error module exists")
        error_attrs = [attr for attr in dir(openai.error) if not attr.startswith('_')]
        print("Available error types:")
        for attr in sorted(error_attrs):
            print(f"  - openai.error.{attr}")
    else:
        print("❌ openai.error module does NOT exist")
    print()
    
    # Check ChatCompletion
    if hasattr(openai, 'ChatCompletion'):
        print("✅ openai.ChatCompletion exists")
    else:
        print("❌ openai.ChatCompletion does NOT exist")
    
    # Check for new client structure
    if hasattr(openai, 'OpenAI'):
        print("✅ openai.OpenAI class exists (new API)")
    else:
        print("❌ openai.OpenAI class does NOT exist")
    
    print()
    print("Testing basic functionality...")
    
    # Try to create a simple request (without API key)
    try:
        # This should fail with auth error, not attribute error
        openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test"}]
        )
    except Exception as e:
        print(f"Expected error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print(f"Error module: {getattr(e, '__module__', 'unknown')}")
    
except ImportError as e:
    print(f"❌ Failed to import openai: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
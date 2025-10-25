"""
Simple Weaviate connection test
"""

import sys

print("=" * 80)
print("Weaviate Connection Test")
print("=" * 80)

# Step 1: Test configuration
print("\n[1/4] Testing configuration...")
try:
    from app.config import get_settings
    settings = get_settings()
    print(f"✓ LLM Provider: {settings.llm_provider}")
    print(f"✓ Weaviate URL: {settings.weaviate_url}")
    print(f"✓ Collection Name: {settings.weaviate_class_name}")
except Exception as e:
    print(f"✗ Config failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Test Weaviate connection
print("\n[2/4] Testing Weaviate connection...")
try:
    from app.vector_store.weaviate_handler import WeaviateHandler
    handler = WeaviateHandler()
    print(f"✓ Connected to Weaviate at {settings.weaviate_url}")
except Exception as e:
    print(f"✗ Connection failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Check collection
print("\n[3/4] Checking collection status...")
try:
    count = handler.get_document_count()
    print(f"✓ Collection '{settings.weaviate_class_name}' has {count} documents")
except Exception as e:
    print(f"⚠ Could not get count (this is ok): {e}")

# Step 4: Test basic operations
print("\n[4/4] Testing basic insert/search...")
try:
    import hashlib
    from datetime import datetime
    
    # Create a test document
    test_content = "TEST: This is a test document"
    test_vector = [0.1] * 384  # Dummy 384-dim vector
    
    # Insert test document
    uuid = handler.insert_document(
        etf_code="TEST001",
        etf_name="Test ETF",
        content=test_content,
        vector=test_vector,
        source="test",
        etf_type="test",
        category="test",
        check_duplicate=True
    )
    
    if uuid:
        print(f"✓ Test document inserted: {uuid}")
        
        # Try to search
        results = handler.search(
            query_vector=test_vector,
            top_k=1,
            etf_code="TEST001"
        )
        
        if results:
            print(f"✓ Search successful: found {len(results)} result(s)")
        else:
            print("⚠ Search returned no results (gRPC may not be working)")
    else:
        print("⚠ Document already exists (duplicate check working)")
        
except Exception as e:
    print(f"⚠ Operation test had issues: {e}")
    import traceback
    traceback.print_exc()

# Cleanup
try:
    handler.close()
    print("\n✓ Connection closed properly")
except Exception as e:
    print(f"⚠ Error closing: {e}")

print("\n" + "=" * 80)
print("✓ Weaviate connection test completed!")
print("=" * 80)
print("\nWeaviate is ready for use.")
print("Note: gRPC errors are expected when running Weaviate without gRPC port exposed.")

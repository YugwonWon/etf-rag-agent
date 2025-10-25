"""
Test embedding model loading and basic functionality
"""

import sys
import time

print("=" * 80)
print("Embedding Model Test")
print("=" * 80)

# Step 1: Test sentence-transformers import
print("\n[1/3] Testing sentence-transformers import...")
try:
    from sentence_transformers import SentenceTransformer
    print("✓ sentence-transformers imported successfully")
except ImportError as e:
    print(f"✗ Failed to import: {e}")
    sys.exit(1)

# Step 2: Load model (this may take time on first run)
print("\n[2/3] Loading embedding model...")
print("  Model: sentence-transformers/all-MiniLM-L6-v2")
print("  (First run will download ~90MB model)")

start_time = time.time()
try:
    embed_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    load_time = time.time() - start_time
    print(f"✓ Model loaded successfully in {load_time:.2f} seconds")
except Exception as e:
    print(f"✗ Failed to load model: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Test encoding
print("\n[3/3] Testing text encoding...")
test_texts = [
    "KODEX 200",
    "This is a test of the S&P 500 ETF",
    "테스트 한글 텍스트"
]

try:
    for i, text in enumerate(test_texts, 1):
        start_time = time.time()
        embedding = embed_model.encode(text)
        encode_time = time.time() - start_time
        
        print(f"  [{i}] '{text[:30]}...'")
        print(f"      Dimension: {len(embedding)}, Time: {encode_time*1000:.1f}ms")
    
    print("\n✓ Encoding test successful!")
    
except Exception as e:
    print(f"✗ Encoding failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ All embedding model tests passed!")
print("=" * 80)
print("\nModel is ready for use in crawler tests.")

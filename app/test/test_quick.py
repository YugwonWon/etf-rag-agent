"""
Quick test - Check if we can insert data into Weaviate
"""

print("=" * 80)
print("Quick Weaviate Insert Test")
print("=" * 80)

print("\n[1/3] Connecting to Weaviate...")
from app.vector_store.weaviate_handler import WeaviateHandler

handler = WeaviateHandler()
print("✓ Connected")

print("\n[2/3] Loading embedding model...")
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
print("✓ Model loaded")

print("\n[3/3] Inserting test data...")

test_data = [
    {
        "code": "KODEX200",
        "name": "KODEX 200",
        "content": "KODEX 200은 코스피200 지수를 추종하는 대표적인 국내 ETF입니다."
    },
    {
        "code": "SPY",
        "name": "SPDR S&P 500 ETF",
        "content": "SPY is one of the largest and most popular ETFs tracking the S&P 500 index."
    }
]

for item in test_data:
    embedding = model.encode(item["content"])
    
    try:
        uuid = handler.insert_document(
            etf_code=item["code"],
            etf_name=item["name"],
            content=item["content"],
            vector=embedding.tolist(),
            source="manual_test",
            etf_type="test",
            category="test",
            check_duplicate=False  # Skip duplicate check to avoid gRPC timeout
        )
        print(f"✓ Inserted: {item['name']} (UUID: {uuid[:8] if uuid else 'None'}...)")
    except Exception as e:
        print(f"✗ Failed to insert {item['name']}: {e}")

handler.close()

print("\n" + "=" * 80)
print("✓ Test completed!")
print("=" * 80)

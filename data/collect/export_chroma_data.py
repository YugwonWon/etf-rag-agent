#!/usr/bin/env python3
"""
Export ChromaDB data to JSON for Docker deployment
This avoids HNSW index file issues in Docker
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def export_chroma_to_json():
    """Export all ChromaDB data to a JSON file"""
    import chromadb
    from chromadb.config import Settings
    
    persist_dir = "./data/chroma"
    collection_name = "ETFDocument"  # Actual collection name
    output_file = "./data/chroma_export.json"
    
    print(f"Connecting to ChromaDB at {persist_dir}...")
    
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True,
        )
    )
    
    collection = client.get_collection(collection_name)
    count = collection.count()
    
    print(f"Found {count} documents in collection '{collection_name}'")
    
    if count == 0:
        print("No documents to export!")
        return
    
    # Get all data
    print("Fetching all documents...")
    all_data = collection.get(
        include=["embeddings", "documents", "metadatas"],
        limit=count
    )
    
    # Prepare export data
    export_data = {
        "collection_name": collection_name,
        "count": len(all_data["ids"]),
        "documents": []
    }
    
    for i, doc_id in enumerate(all_data["ids"]):
        embedding = all_data["embeddings"][i]
        # Convert numpy array to list if needed
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()
        
        doc = {
            "id": doc_id,
            "embedding": embedding,
            "document": all_data["documents"][i] if all_data["documents"] else "",
            "metadata": all_data["metadatas"][i] if all_data["metadatas"] else {}
        }
        export_data["documents"].append(doc)
    
    # Save to JSON
    print(f"Saving to {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False)
    
    # Check file size
    file_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"✓ Exported {len(export_data['documents'])} documents to {output_file} ({file_size:.1f} MB)")
    
    return output_file


if __name__ == "__main__":
    export_chroma_to_json()

"""
ChromaDB Vector Store Handler
Manages ETF document storage and retrieval in ChromaDB
Compatible with WeaviateHandler API
"""

import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from loguru import logger
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("chromadb not installed")


class ChromaHandler:
    """Handler for ChromaDB vector database operations"""
    
    def __init__(
        self,
        persist_directory: str = None,
        collection_name: str = None
    ):
        """
        Initialize ChromaDB client
        
        Args:
            persist_directory: Directory to persist data
            collection_name: Collection name
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("chromadb is required. Install with: pip install chromadb")
        
        from app.config import get_settings
        settings = get_settings()
        
        # Set persist directory (default: ./data/chroma)
        self.persist_directory = persist_directory or str(
            settings.data_dir / "chroma"
        )
        self.collection_name = collection_name or settings.chroma_collection_name
        
        # Ensure directory exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Connect to ChromaDB
        try:
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            logger.info(f"Connected to ChromaDB at {self.persist_directory}")
            
            # Ensure collection exists
            self._ensure_collection()
            
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "ETF documents for RAG"}
            )
            
            logger.info(f"Collection '{self.collection_name}' ready with {self.collection.count()} documents")
                
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
            raise
    
    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA256 hash of content"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _check_duplicate(
        self,
        etf_code: str,
        content_hash: str
    ) -> bool:
        """
        Check if document with same content already exists
        
        Args:
            etf_code: ETF code
            content_hash: Content hash
        
        Returns:
            True if duplicate exists
        """
        try:
            results = self.collection.get(
                where={
                    "$and": [
                        {"etf_code": {"$eq": etf_code}},
                        {"content_hash": {"$eq": content_hash}}
                    ]
                },
                limit=1
            )
            
            return len(results["ids"]) > 0
            
        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")
            return False
    
    def _get_latest_version(self, etf_code: str) -> int:
        """Get the latest version number for an ETF"""
        try:
            results = self.collection.get(
                where={"etf_code": {"$eq": etf_code}},
                include=["metadatas"]
            )
            
            if results["ids"]:
                versions = [
                    m.get("version", 0) 
                    for m in results["metadatas"]
                ]
                return max(versions) if versions else 0
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting latest version: {e}")
            return 0
    
    def insert_document(
        self,
        etf_code: str,
        etf_name: str,
        content: str,
        vector: List[float],
        source: str,
        etf_type: str,
        category: str = "",
        additional_metadata: Dict[str, Any] = None,
        check_duplicate: bool = True
    ) -> Optional[str]:
        """
        Insert document into ChromaDB
        
        Args:
            etf_code: ETF ticker/code
            etf_name: ETF name
            content: Document content
            vector: Embedding vector
            source: Data source
            etf_type: "domestic" or "foreign"
            category: ETF category
            additional_metadata: Additional metadata dict
            check_duplicate: Check for duplicates before insert
        
        Returns:
            Document ID if inserted, None if duplicate
        """
        try:
            content_hash = self._compute_content_hash(content)
            
            # Check duplicate if enabled
            from app.config import get_settings
            settings = get_settings()
            
            if check_duplicate and settings.enable_duplicate_check:
                if self._check_duplicate(etf_code, content_hash):
                    logger.info(f"Duplicate document found for {etf_code}, skipping")
                    return None
            
            # Get next version
            if settings.keep_history:
                version = self._get_latest_version(etf_code) + 1
            else:
                version = 1
            
            # Generate unique ID
            doc_id = f"{etf_code}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{version}"
            
            # Prepare metadata (ChromaDB metadata must be flat)
            metadata = {
                "etf_code": etf_code,
                "etf_name": etf_name,
                "content_hash": content_hash,
                "date": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "version": version,
                "source": source,
                "etf_type": etf_type,
                "category": category,
            }
            
            # Add additional metadata (flatten if needed)
            if additional_metadata:
                for key, value in additional_metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        metadata[key] = value
                    else:
                        # Store complex types as JSON string
                        metadata[f"{key}_json"] = json.dumps(value, ensure_ascii=False)
            
            # Insert document
            self.collection.add(
                ids=[doc_id],
                embeddings=[vector],
                documents=[content],
                metadatas=[metadata]
            )
            
            logger.info(
                f"Inserted document: {etf_code} (v{version}) - ID: {doc_id}"
            )
            
            return doc_id
            
        except Exception as e:
            logger.error(f"Error inserting document: {e}")
            raise
    
    def insert_documents_batch(
        self,
        documents: List[Dict[str, Any]],
        check_duplicate: bool = True
    ) -> List[Optional[str]]:
        """
        Insert multiple documents in batch
        
        Args:
            documents: List of document dicts with required fields
            check_duplicate: Check for duplicates
        
        Returns:
            List of IDs (None for duplicates)
        """
        ids = []
        
        for doc in documents:
            doc_id = self.insert_document(
                etf_code=doc["etf_code"],
                etf_name=doc["etf_name"],
                content=doc["content"],
                vector=doc["vector"],
                source=doc["source"],
                etf_type=doc["etf_type"],
                category=doc.get("category", ""),
                additional_metadata=doc.get("metadata"),
                check_duplicate=check_duplicate
            )
            ids.append(doc_id)
        
        logger.info(
            f"Batch insert completed: {sum(1 for i in ids if i is not None)}/{len(documents)} documents"
        )
        
        return ids
    
    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        min_certainty: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query_vector: Query embedding vector
            limit: Number of results
            filters: Filter conditions (e.g., {"etf_type": "domestic"})
            min_certainty: Minimum similarity score (0-1)
        
        Returns:
            List of search results with content and metadata
        """
        try:
            # Build filter (ChromaDB where clause)
            where_clause = None
            if filters:
                if len(filters) == 1:
                    key, value = list(filters.items())[0]
                    where_clause = {key: {"$eq": value}}
                else:
                    where_clause = {
                        "$and": [
                            {key: {"$eq": value}} 
                            for key, value in filters.items()
                        ]
                    }
            
            # Search
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=limit,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    # Convert distance to certainty (ChromaDB uses L2 distance by default)
                    # Lower distance = higher similarity
                    distance = results["distances"][0][i] if results["distances"] else 0
                    # Convert L2 distance to similarity score (approximate)
                    certainty = 1 / (1 + distance)
                    
                    if certainty >= min_certainty:
                        metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                        
                        formatted_results.append({
                            "uuid": doc_id,
                            "content": results["documents"][0][i] if results["documents"] else "",
                            "certainty": certainty,
                            "metadata": {
                                "etf_code": metadata.get("etf_code"),
                                "etf_name": metadata.get("etf_name"),
                                "date": metadata.get("date"),
                                "version": metadata.get("version"),
                                "source": metadata.get("source"),
                                "etf_type": metadata.get("etf_type"),
                                "category": metadata.get("category"),
                            }
                        })
            
            logger.debug(f"Search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching: {e}")
            raise
    
    def delete_old_versions(
        self,
        etf_code: str,
        keep_versions: int = 10
    ):
        """Delete old versions of an ETF document"""
        try:
            results = self.collection.get(
                where={"etf_code": {"$eq": etf_code}},
                include=["metadatas"]
            )
            
            if len(results["ids"]) <= keep_versions:
                return
            
            # Sort by version
            versioned = list(zip(results["ids"], results["metadatas"]))
            versioned.sort(
                key=lambda x: x[1].get("version", 0),
                reverse=True
            )
            
            # Delete old versions
            ids_to_delete = [v[0] for v in versioned[keep_versions:]]
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
                logger.info(
                    f"Cleaned up old versions for {etf_code}: "
                    f"kept {keep_versions}, deleted {len(ids_to_delete)}"
                )
            
        except Exception as e:
            logger.error(f"Error deleting old versions: {e}")
    
    def get_document_count(self) -> int:
        """Get total document count"""
        try:
            return self.collection.count()
        except Exception as e:
            logger.warning(f"Error getting count: {e}")
            return 0
    
    def get_etf_codes_needing_update(self, days: int = 7) -> List[str]:
        """
        Get ETF codes that need updating (last updated more than N days ago or never updated)
        
        Args:
            days: Number of days threshold
            
        Returns:
            List of ETF codes that need updating
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Get all documents
            results = self.collection.get(
                include=["metadatas"]
            )
            
            if not results["ids"]:
                return []
            
            # Group by ETF code and find latest date
            etf_latest_date = {}
            for metadata in results["metadatas"]:
                code = metadata.get("etf_code")
                date = metadata.get("date", "")
                
                if code:
                    if code not in etf_latest_date or date > etf_latest_date[code]:
                        etf_latest_date[code] = date
            
            # Find codes that need updating
            codes_needing_update = [
                code for code, date in etf_latest_date.items()
                if date < cutoff_date
            ]
            
            logger.info(f"Found {len(codes_needing_update)} ETFs needing update (older than {days} days)")
            return codes_needing_update
            
        except Exception as e:
            logger.error(f"Error getting ETF codes needing update: {e}")
            return []
    
    def get_source_counts(self) -> Dict[str, int]:
        """
        Get document count by source
        
        Returns:
            Dictionary mapping source to document count
        """
        try:
            sources = ["naver", "yfinance", "dart"]
            counts = {}
            
            for source in sources:
                results = self.collection.get(
                    where={"source": {"$eq": source}}
                )
                counts[source] = len(results["ids"])
                logger.debug(f"Source '{source}': {counts[source]} documents")
            
            return counts
            
        except Exception as e:
            logger.error(f"Error getting source counts: {e}")
            return {}
    
    def delete_all(self):
        """Delete all documents in collection"""
        try:
            # Get all IDs
            results = self.collection.get()
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted all {len(results['ids'])} documents")
        except Exception as e:
            logger.error(f"Error deleting all documents: {e}")
    
    def close(self):
        """Close ChromaDB connection (no-op for PersistentClient)"""
        logger.info("ChromaDB connection closed")


# Alias for compatibility
VectorHandler = ChromaHandler


# Example usage
if __name__ == "__main__":
    logger.info("Testing ChromaDB Handler...")
    
    try:
        handler = ChromaHandler()
        
        # Test insert
        test_vector = [0.1] * 1536  # Dummy vector
        
        doc_id = handler.insert_document(
            etf_code="069500",
            etf_name="KODEX 200",
            content="KODEX 200은 코스피 200 지수를 추종하는 대표적인 국내 ETF입니다.",
            vector=test_vector,
            source="test",
            etf_type="domestic",
            category="국내주식"
        )
        
        print(f"Inserted document ID: {doc_id}")
        
        # Test search
        results = handler.search(
            query_vector=test_vector,
            limit=5
        )
        
        print(f"\nSearch results: {len(results)}")
        for result in results:
            print(f"- {result['metadata']['etf_name']}: {result['certainty']:.2f}")
        
        # Get count
        count = handler.get_document_count()
        print(f"\nTotal documents: {count}")
        
        handler.close()
        
    except Exception as e:
        logger.error(f"Error: {e}")

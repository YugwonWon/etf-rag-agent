"""
Weaviate Vector Store Handler
Manages ETF document storage and retrieval in Weaviate
"""

import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from loguru import logger

try:
    import weaviate
    from weaviate.classes.init import Auth
    from weaviate.classes.config import Configure, Property, DataType
    from weaviate.classes.query import Filter, MetadataQuery
    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False
    logger.warning("weaviate-client not installed")


class WeaviateHandler:
    """Handler for Weaviate vector database operations"""
    
    def __init__(
        self,
        url: str = None,
        api_key: str = None,
        class_name: str = None
    ):
        """
        Initialize Weaviate client
        
        Args:
            url: Weaviate instance URL
            api_key: API key (optional for local)
            class_name: Collection/Class name
        """
        if not WEAVIATE_AVAILABLE:
            raise ImportError("weaviate-client is required. Install with: pip install weaviate-client")
        
        from app.config import get_settings
        settings = get_settings()
        
        self.url = url or settings.weaviate_url
        self.api_key = api_key or settings.weaviate_api_key
        self.class_name = class_name or settings.weaviate_class_name
        
        # Connect to Weaviate
        try:
            if self.api_key:
                self.client = weaviate.connect_to_wcs(
                    cluster_url=self.url,
                    auth_credentials=Auth.api_key(self.api_key)
                )
            else:
                self.client = weaviate.connect_to_local(
                    host=self.url.replace("http://", "").replace("https://", "").split(":")[0],
                    port=int(self.url.split(":")[-1]) if ":" in self.url else 8080
                )
            
            logger.info(f"Connected to Weaviate at {self.url}")
            
            # Ensure collection exists
            self._ensure_collection()
            
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            raise
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            # Check if collection exists
            collections = self.client.collections.list_all()
            
            if self.class_name not in [c.name for c in collections]:
                logger.info(f"Creating collection: {self.class_name}")
                
                # Create collection with schema
                self.client.collections.create(
                    name=self.class_name,
                    vectorizer_config=Configure.Vectorizer.none(),  # We'll provide our own vectors
                    properties=[
                        Property(name="etf_code", data_type=DataType.TEXT),
                        Property(name="etf_name", data_type=DataType.TEXT),
                        Property(name="content", data_type=DataType.TEXT),
                        Property(name="content_hash", data_type=DataType.TEXT),
                        Property(name="date", data_type=DataType.DATE),
                        Property(name="version", data_type=DataType.INT),
                        Property(name="source", data_type=DataType.TEXT),
                        Property(name="etf_type", data_type=DataType.TEXT),  # domestic/foreign
                        Property(name="category", data_type=DataType.TEXT),
                        Property(name="metadata_json", data_type=DataType.TEXT),
                    ]
                )
                logger.info(f"Collection {self.class_name} created successfully")
            else:
                logger.info(f"Collection {self.class_name} already exists")
                
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
            collection = self.client.collections.get(self.class_name)
            
            results = collection.query.fetch_objects(
                filters=Filter.by_property("etf_code").equal(etf_code) &
                        Filter.by_property("content_hash").equal(content_hash),
                limit=1
            )
            
            return len(results.objects) > 0
            
        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")
            return False
    
    def _get_latest_version(self, etf_code: str) -> int:
        """Get the latest version number for an ETF"""
        try:
            collection = self.client.collections.get(self.class_name)
            
            results = collection.query.fetch_objects(
                filters=Filter.by_property("etf_code").equal(etf_code),
                limit=1,
                return_properties=["version"],
            )
            
            if results.objects:
                # Get max version
                versions = [obj.properties.get("version", 0) for obj in results.objects]
                return max(versions)
            
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
        Insert document into Weaviate
        
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
            Document UUID if inserted, None if duplicate
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
            
            # Prepare metadata
            metadata = additional_metadata or {}
            metadata.update({
                "etf_code": etf_code,
                "etf_name": etf_name,
                "source": source,
                "etf_type": etf_type,
            })
            
            # Insert document
            collection = self.client.collections.get(self.class_name)
            
            uuid = collection.data.insert(
                properties={
                    "etf_code": etf_code,
                    "etf_name": etf_name,
                    "content": content,
                    "content_hash": content_hash,
                    "date": datetime.now().isoformat(),
                    "version": version,
                    "source": source,
                    "etf_type": etf_type,
                    "category": category,
                    "metadata_json": json.dumps(metadata, ensure_ascii=False),
                },
                vector=vector
            )
            
            logger.info(
                f"Inserted document: {etf_code} (v{version}) - UUID: {uuid}"
            )
            
            return str(uuid)
            
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
            List of UUIDs (None for duplicates)
        """
        uuids = []
        
        for doc in documents:
            uuid = self.insert_document(
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
            uuids.append(uuid)
        
        logger.info(
            f"Batch insert completed: {sum(1 for u in uuids if u is not None)}/{len(documents)} documents"
        )
        
        return uuids
    
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
            collection = self.client.collections.get(self.class_name)
            
            # Build filter
            filter_obj = None
            if filters:
                filter_conditions = []
                for key, value in filters.items():
                    filter_conditions.append(
                        Filter.by_property(key).equal(value)
                    )
                
                if len(filter_conditions) == 1:
                    filter_obj = filter_conditions[0]
                else:
                    filter_obj = filter_conditions[0]
                    for condition in filter_conditions[1:]:
                        filter_obj = filter_obj & condition
            
            # Search
            results = collection.query.near_vector(
                near_vector=query_vector,
                limit=limit,
                filters=filter_obj,
                return_metadata=MetadataQuery(certainty=True),
            )
            
            # Format results
            formatted_results = []
            for obj in results.objects:
                props = obj.properties
                metadata_json = props.get("metadata_json", "{}")
                metadata = json.loads(metadata_json) if metadata_json else {}
                
                # Add certainty to metadata
                certainty = obj.metadata.certainty if hasattr(obj.metadata, 'certainty') else 0
                
                if certainty >= min_certainty:
                    formatted_results.append({
                        "uuid": str(obj.uuid),
                        "content": props.get("content", ""),
                        "certainty": certainty,
                        "metadata": {
                            "etf_code": props.get("etf_code"),
                            "etf_name": props.get("etf_name"),
                            "date": props.get("date"),
                            "version": props.get("version"),
                            "source": props.get("source"),
                            "etf_type": props.get("etf_type"),
                            "category": props.get("category"),
                            **metadata
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
            collection = self.client.collections.get(self.class_name)
            
            # Get all versions
            results = collection.query.fetch_objects(
                filters=Filter.by_property("etf_code").equal(etf_code),
                return_properties=["version"],
            )
            
            if len(results.objects) <= keep_versions:
                return
            
            # Sort by version
            versions = sorted(
                results.objects,
                key=lambda x: x.properties.get("version", 0),
                reverse=True
            )
            
            # Delete old versions
            for obj in versions[keep_versions:]:
                collection.data.delete_by_id(obj.uuid)
                logger.debug(f"Deleted old version: {obj.uuid}")
            
            logger.info(
                f"Cleaned up old versions for {etf_code}: "
                f"kept {keep_versions}, deleted {len(versions) - keep_versions}"
            )
            
        except Exception as e:
            logger.error(f"Error deleting old versions: {e}")
    
    def get_document_count(self) -> int:
        """Get total document count"""
        try:
            collection = self.client.collections.get(self.class_name)
            aggregate = collection.aggregate.over_all(total_count=True)
            return aggregate.total_count
        except Exception as e:
            logger.error(f"Error getting count: {e}")
            return 0
    
    def close(self):
        """Close Weaviate connection"""
        try:
            self.client.close()
            logger.info("Weaviate connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")


# Example usage
if __name__ == "__main__":
    logger.info("Testing Weaviate Handler...")
    
    try:
        handler = WeaviateHandler()
        
        # Test insert
        test_vector = [0.1] * 1536  # Dummy vector
        
        uuid = handler.insert_document(
            etf_code="069500",
            etf_name="KODEX 200",
            content="KODEX 200은 코스피 200 지수를 추종하는 대표적인 국내 ETF입니다.",
            vector=test_vector,
            source="test",
            etf_type="domestic",
            category="국내주식"
        )
        
        print(f"Inserted document UUID: {uuid}")
        
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

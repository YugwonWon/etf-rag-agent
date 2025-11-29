"""
Vector Store Factory
Provides unified interface for different vector databases
"""

from typing import Union
from loguru import logger

from app.config import get_settings


def get_vector_handler():
    """
    Get the appropriate vector handler based on configuration
    
    Returns:
        ChromaHandler or WeaviateHandler instance
    """
    settings = get_settings()
    db_type = settings.vector_db_type.lower()
    
    if db_type == "chroma":
        from app.vector_store.chroma_handler import ChromaHandler
        logger.info("Using ChromaDB as vector store")
        return ChromaHandler(
            persist_directory=settings.chroma_persist_directory,
            collection_name=settings.chroma_collection_name
        )
    elif db_type == "weaviate":
        from app.vector_store.weaviate_handler import WeaviateHandler
        logger.info("Using Weaviate as vector store")
        return WeaviateHandler(
            url=settings.weaviate_url,
            api_key=settings.weaviate_api_key,
            class_name=settings.weaviate_class_name
        )
    else:
        raise ValueError(f"Unknown vector DB type: {db_type}. Use 'chroma' or 'weaviate'")


# Type alias for handlers
VectorHandler = Union["ChromaHandler", "WeaviateHandler"]

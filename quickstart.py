"""
Quick Start Script for ETF RAG Agent
Run this after setup to test the system
"""

import sys
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO")

def main():
    """Main quick start function"""
    
    print("=" * 60)
    print("ETF RAG Agent - Quick Start")
    print("=" * 60)
    
    # Step 1: Check configuration
    print("\n[1/5] Checking configuration...")
    try:
        from app.config import get_settings, validate_config
        settings = get_settings()
        validate_config()
        logger.info(f"✓ LLM Provider: {settings.llm_provider}")
        logger.info(f"✓ Weaviate URL: {settings.weaviate_url}")
    except Exception as e:
        logger.error(f"✗ Configuration error: {e}")
        logger.info("Please check your .env file")
        return
    
    # Step 2: Test Weaviate connection
    print("\n[2/5] Testing Weaviate connection...")
    try:
        from app.vector_store.weaviate_handler import WeaviateHandler
        handler = WeaviateHandler()
        count = handler.get_document_count()
        logger.info(f"✓ Connected to Weaviate: {count} documents")
        handler.close()
    except Exception as e:
        logger.error(f"✗ Weaviate connection failed: {e}")
        logger.info("Please start Weaviate: docker run -d -p 8080:8080 semitechnologies/weaviate:latest")
        return
    
    # Step 3: Test LLM model
    print("\n[3/5] Testing LLM model...")
    try:
        from app.model.model_factory import get_model
        model = get_model()
        logger.info(f"✓ LLM model loaded: {type(model).__name__}")
    except Exception as e:
        logger.error(f"✗ LLM model error: {e}")
        logger.info("Please check your API keys in .env file")
        return
    
    # Step 4: Collect sample data
    print("\n[4/5] Collecting sample ETF data...")
    print("This may take a few minutes...")
    try:
        from app.crawler.collector import ETFDataCollector
        from app.vector_store.weaviate_handler import WeaviateHandler
        
        handler = WeaviateHandler()
        collector = ETFDataCollector(
            vector_handler=handler,
            model_type=settings.llm_provider
        )
        
        # Collect small sample
        results = collector.collect_all(
            domestic_max=3,
            foreign_tickers=["SPY", "QQQ"],
            dart_days=7,
            insert_to_db=True
        )
        
        logger.info(f"✓ Data collected: {results['total']} items")
        logger.info(f"  - Domestic: {len(results['domestic'])}")
        logger.info(f"  - Foreign: {len(results['foreign'])}")
        logger.info(f"  - DART: {len(results['dart'])}")
        
        handler.close()
    except Exception as e:
        logger.error(f"✗ Data collection error: {e}")
        return
    
    # Step 5: Test query
    print("\n[5/5] Testing query...")
    try:
        from app.retriever.query_handler import RAGQueryHandler
        
        handler = RAGQueryHandler(model_type=settings.llm_provider)
        
        test_question = "수집된 ETF 중 하나를 설명해주세요"
        logger.info(f"Question: {test_question}")
        
        response = handler.query(test_question)
        
        print("\n" + "=" * 60)
        print("답변:")
        print("-" * 60)
        print(response['answer'])
        print("-" * 60)
        print(f"참고 문서: {response['num_sources']}개")
        print("=" * 60)
        
        handler.close()
        
    except Exception as e:
        logger.error(f"✗ Query test error: {e}")
        return
    
    # Success
    print("\n" + "=" * 60)
    print("✓ Quick start completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start REST API server: python -m app.main")
    print("2. Visit API docs: http://localhost:8000/docs")
    print("3. Start gRPC server: python -m app.connect_rpc")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nQuick start interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

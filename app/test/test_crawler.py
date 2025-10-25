"""
Test script for ETF crawler and vector DB
"""

import sys
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO")

def test_crawlers():
    """Test ETF crawlers and vector DB insertion"""
    
    print("=" * 80)
    print("ETF RAG Agent - Crawler Test")
    print("=" * 80)
    
    # Step 1: Test configuration
    print("\n[1/6] Testing configuration...")
    from app.config import get_settings
    settings = get_settings()
    logger.info(f"✓ LLM Provider: {settings.llm_provider}")
    logger.info(f"✓ Weaviate URL: {settings.weaviate_url}")
    
    # Step 2: Test Weaviate connection
    print("\n[2/6] Testing Weaviate connection...")
    from app.vector_store.weaviate_handler import WeaviateHandler
    handler = WeaviateHandler()
    count = handler.get_document_count()
    logger.info(f"✓ Connected to Weaviate: {count} documents")
    
    # Step 3: Test embedding model (use local sentence-transformers)
    print("\n[3/6] Testing embedding model...")
    from sentence_transformers import SentenceTransformer
    
    embed_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    test_embedding = embed_model.encode("테스트")
    logger.info(f"✓ Embedding model working: dimension {len(test_embedding)}")
    
    # Step 4: Collect sample domestic ETFs
    print("\n[4/6] Collecting sample domestic ETFs (3개)...")
    from app.crawler.naver_kr import NaverETFCrawler
    
    naver_crawler = NaverETFCrawler()
    etfs = naver_crawler.get_all_etf_details(max_items=3, delay=1)
    logger.info(f"✓ Collected {len(etfs)} domestic ETFs")
    
    if etfs:
        sample = etfs[0]
        logger.info(f"  Example: {sample['name']} ({sample['code']})")
    
    # Step 5: Insert into vector DB
    print("\n[5/6] Inserting into vector DB...")
    inserted_count = 0
    
    for etf in etfs:
        formatted = naver_crawler.format_for_vector_db(etf)
        embedding = embed_model.encode(formatted['content'])
        
        uuid = handler.insert_document(
            etf_code=formatted['etf_code'],
            etf_name=formatted['etf_name'],
            content=formatted['content'],
            vector=embedding.tolist(),  # Convert numpy array to list
            source=formatted['source'],
            etf_type=formatted['etf_type'],
            category=formatted.get('category', ''),
            additional_metadata=formatted.get('metadata'),
            check_duplicate=True
        )
        
        if uuid:
            inserted_count += 1
            logger.info(f"  ✓ Inserted: {formatted['etf_name']}")
    
    logger.info(f"✓ Inserted {inserted_count} documents into vector DB")
    
    # Step 6: Test foreign ETFs
    print("\n[6/6] Collecting sample foreign ETFs (2개)...")
    from app.crawler.yfinance_us import YFinanceETFCrawler
    
    yfinance_crawler = YFinanceETFCrawler()
    foreign_etfs = yfinance_crawler.get_all_etf_info(tickers=["SPY", "QQQ"])
    logger.info(f"✓ Collected {len(foreign_etfs)} foreign ETFs")
    
    for fetf in foreign_etfs:
        formatted = yfinance_crawler.format_for_vector_db(fetf)
        embedding = embed_model.encode(formatted['content'])
        
        uuid = handler.insert_document(
            etf_code=formatted['etf_code'],
            etf_name=formatted['etf_name'],
            content=formatted['content'],
            vector=embedding.tolist(),  # Convert numpy array to list
            source=formatted['source'],
            etf_type=formatted['etf_type'],
            category=formatted.get('category', ''),
            additional_metadata=formatted.get('metadata'),
            check_duplicate=True
        )
        
        if uuid:
            logger.info(f"  ✓ Inserted: {formatted['etf_name']}")
    
    # Final status
    total_docs = handler.get_document_count()
    logger.info(f"\n✓ Total documents in vector DB: {total_docs}")
    
    handler.close()
    
    print("\n" + "=" * 80)
    print("✓ Crawler test completed successfully!")
    print("=" * 80)
    print(f"\nNext: Test RAG query system")
    print(f"  Run: python test_rag.py")
    print("=" * 80)


if __name__ == "__main__":
    try:
        test_crawlers()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

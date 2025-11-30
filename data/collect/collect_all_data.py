#!/usr/bin/env python3
"""
ETF Data Collection Script for ChromaDB
Collects ETF data and stores in ChromaDB vector store
"""

import argparse
import sys
import os
from pathlib import Path
from loguru import logger

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Set default environment variables for debug
os.environ.setdefault("VECTOR_DB_TYPE", "chroma")
os.environ.setdefault("CHROMA_PERSIST_DIRECTORY", "./data/chroma")
os.environ.setdefault("CHROMA_COLLECTION_NAME", "ETFDocument")
os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))

def main():
    parser = argparse.ArgumentParser(description='Collect ETF data into ChromaDB')
    parser.add_argument('--domestic-max', type=int, default=None, help='Max domestic ETFs to collect')
    parser.add_argument('--foreign-max', type=int, default=None, help='Max foreign ETFs to collect')
    parser.add_argument('--dart-max', type=int, default=None, help='Max DART docs to collect')
    parser.add_argument('--skip-outdated-check', action='store_true', help='Skip outdated check, collect all')
    parser.add_argument('--no-domestic', action='store_true', help='Skip domestic ETFs')
    parser.add_argument('--no-foreign', action='store_true', help='Skip foreign ETFs')
    parser.add_argument('--no-dart', action='store_true', help='Skip DART docs')
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("ETF Data Collection Started (ChromaDB)")
    logger.info("=" * 60)
    
    # Import after parsing args to avoid slow startup for --help
    from app.vector_store import get_vector_handler
    from app.crawler.collector import ETFDataCollector
    from app.config import get_settings
    
    settings = get_settings()
    
    # Initialize vector handler
    logger.info(f"Vector DB Type: {settings.vector_db_type}")
    vector_handler = get_vector_handler()
    logger.info(f"Initial document count: {vector_handler.get_document_count()}")
    
    # Initialize collector
    collector = ETFDataCollector(
        vector_handler=vector_handler,
        model_type='openai'
    )
    
    # Determine what to collect
    only_outdated = not args.skip_outdated_check
    
    results = {
        'domestic': 0,
        'foreign': 0,
        'dart': 0
    }
    
    # Collect domestic ETFs
    if not args.no_domestic:
        logger.info(f"Collecting domestic ETFs (max: {args.domestic_max or 'all'})...")
        try:
            etfs = collector.collect_domestic_etfs(
                max_items=args.domestic_max,
                insert_to_db=True,
                only_outdated=only_outdated
            )
            results['domestic'] = len(etfs)
            logger.info(f"✅ Domestic ETFs collected: {len(etfs)}")
        except Exception as e:
            logger.error(f"❌ Error collecting domestic ETFs: {e}")
    
    # Collect foreign ETFs
    if not args.no_foreign:
        logger.info(f"Collecting foreign ETFs (max: {args.foreign_max or 'all'})...")
        try:
            etfs = collector.collect_foreign_etfs(
                insert_to_db=True,
                max_items=args.foreign_max
            )
            results['foreign'] = len(etfs)
            logger.info(f"✅ Foreign ETFs collected: {len(etfs)}")
        except Exception as e:
            logger.error(f"❌ Error collecting foreign ETFs: {e}")
    
    # Collect DART disclosures
    if not args.no_dart:
        logger.info(f"Collecting DART disclosures (max: {args.dart_max or 'all'})...")
        try:
            docs = collector.collect_dart_disclosures(
                insert_to_db=True,
                max_items=args.dart_max
            )
            results['dart'] = len(docs)
            logger.info(f"✅ DART docs collected: {len(docs)}")
        except Exception as e:
            logger.error(f"❌ Error collecting DART docs: {e}")
    
    # Summary
    logger.info("=" * 60)
    logger.info("Collection Summary")
    logger.info("=" * 60)
    logger.info(f"Domestic ETFs: {results['domestic']}")
    logger.info(f"Foreign ETFs: {results['foreign']}")
    logger.info(f"DART Docs: {results['dart']}")
    logger.info(f"Total: {sum(results.values())}")
    logger.info(f"Final document count: {vector_handler.get_document_count()}")
    logger.info("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

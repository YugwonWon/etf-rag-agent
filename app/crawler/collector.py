"""
Unified ETF Data Collector
Orchestrates all crawlers and vector DB insertion
"""

from typing import List, Dict, Optional
from loguru import logger

from app.crawler.naver_kr import NaverETFCrawler
from app.crawler.yfinance_us import YFinanceETFCrawler
from app.crawler.dart_api import DARTCrawler
from app.vector_store.weaviate_handler import WeaviateHandler
from app.model.model_factory import get_model


class ETFDataCollector:
    """Unified collector for all ETF data sources"""
    
    def __init__(
        self,
        vector_handler: Optional[WeaviateHandler] = None,
        model_type: str = None
    ):
        """
        Initialize collector
        
        Args:
            vector_handler: WeaviateHandler instance
            model_type: LLM model type for embeddings
        """
        self.naver_crawler = NaverETFCrawler()
        self.yfinance_crawler = YFinanceETFCrawler()
        self.dart_crawler = DARTCrawler()
        
        self.vector_handler = vector_handler
        self.model = get_model(model_type) if model_type else None
        
        logger.info("ETF Data Collector initialized")
    
    def collect_domestic_etfs(
        self,
        max_items: Optional[int] = None,
        insert_to_db: bool = False
    ) -> List[Dict[str, any]]:
        """
        Collect domestic ETF data from Naver
        
        Args:
            max_items: Maximum number of ETFs to collect
            insert_to_db: Whether to insert into vector DB
        
        Returns:
            List of formatted ETF data
        """
        logger.info("Collecting domestic ETFs from Naver...")
        
        # Crawl ETFs
        etfs = self.naver_crawler.get_all_etf_details(
            max_items=max_items,
            delay=0.5
        )
        
        # Format for vector DB
        formatted_etfs = []
        for etf in etfs:
            formatted = self.naver_crawler.format_for_vector_db(etf)
            formatted_etfs.append(formatted)
        
        logger.info(f"Formatted {len(formatted_etfs)} domestic ETFs")
        
        # Insert to vector DB if requested
        if insert_to_db and self.vector_handler and self.model:
            self._insert_to_vector_db(formatted_etfs)
        
        return formatted_etfs
    
    def collect_foreign_etfs(
        self,
        tickers: Optional[List[str]] = None,
        insert_to_db: bool = False
    ) -> List[Dict[str, any]]:
        """
        Collect foreign ETF data from yfinance
        
        Args:
            tickers: List of tickers (uses default if None)
            insert_to_db: Whether to insert into vector DB
        
        Returns:
            List of formatted ETF data
        """
        logger.info("Collecting foreign ETFs from yfinance...")
        
        # Crawl ETFs
        etfs = self.yfinance_crawler.get_all_etf_info(tickers=tickers)
        
        # Format for vector DB
        formatted_etfs = []
        for etf in etfs:
            formatted = self.yfinance_crawler.format_for_vector_db(etf)
            formatted_etfs.append(formatted)
        
        logger.info(f"Formatted {len(formatted_etfs)} foreign ETFs")
        
        # Insert to vector DB if requested
        if insert_to_db and self.vector_handler and self.model:
            self._insert_to_vector_db(formatted_etfs)
        
        return formatted_etfs
    
    def collect_dart_disclosures(
        self,
        days_back: int = 30,
        insert_to_db: bool = False
    ) -> List[Dict[str, any]]:
        """
        Collect ETF disclosure documents from DART
        
        Args:
            days_back: Number of days to look back
            insert_to_db: Whether to insert into vector DB
        
        Returns:
            List of formatted disclosure data
        """
        logger.info("Collecting ETF disclosures from DART...")
        
        # Crawl disclosures
        disclosures = self.dart_crawler.get_etf_prospectus_list(days_back=days_back)
        
        # Format for vector DB
        formatted_disclosures = []
        for disclosure in disclosures:
            formatted = self.dart_crawler.format_for_vector_db(disclosure)
            formatted_disclosures.append(formatted)
        
        logger.info(f"Formatted {len(formatted_disclosures)} DART disclosures")
        
        # Insert to vector DB if requested
        if insert_to_db and self.vector_handler and self.model:
            self._insert_to_vector_db(formatted_disclosures)
        
        return formatted_disclosures
    
    def collect_all(
        self,
        domestic_max: Optional[int] = None,
        foreign_tickers: Optional[List[str]] = None,
        dart_days: int = 30,
        insert_to_db: bool = True
    ) -> Dict[str, any]:
        """
        Collect all ETF data from all sources
        
        Args:
            domestic_max: Max domestic ETFs
            foreign_tickers: Foreign ETF tickers
            dart_days: DART lookback days
            insert_to_db: Whether to insert into vector DB
        
        Returns:
            Summary dict with counts
        """
        logger.info("=== Starting full ETF data collection ===")
        
        results = {
            "domestic": [],
            "foreign": [],
            "dart": [],
            "total": 0,
            "inserted": 0
        }
        
        # Collect domestic
        try:
            domestic = self.collect_domestic_etfs(
                max_items=domestic_max,
                insert_to_db=insert_to_db
            )
            results["domestic"] = domestic
        except Exception as e:
            logger.error(f"Error collecting domestic ETFs: {e}")
        
        # Collect foreign
        try:
            foreign = self.collect_foreign_etfs(
                tickers=foreign_tickers,
                insert_to_db=insert_to_db
            )
            results["foreign"] = foreign
        except Exception as e:
            logger.error(f"Error collecting foreign ETFs: {e}")
        
        # Collect DART
        try:
            dart = self.collect_dart_disclosures(
                days_back=dart_days,
                insert_to_db=insert_to_db
            )
            results["dart"] = dart
        except Exception as e:
            logger.error(f"Error collecting DART disclosures: {e}")
        
        results["total"] = (
            len(results["domestic"]) +
            len(results["foreign"]) +
            len(results["dart"])
        )
        
        logger.info(f"=== Collection complete ===")
        logger.info(f"  Domestic: {len(results['domestic'])}")
        logger.info(f"  Foreign: {len(results['foreign'])}")
        logger.info(f"  DART: {len(results['dart'])}")
        logger.info(f"  Total: {results['total']}")
        
        return results
    
    def _insert_to_vector_db(
        self,
        formatted_data: List[Dict[str, any]]
    ):
        """
        Insert formatted data into vector DB with embeddings
        
        Args:
            formatted_data: List of formatted ETF dicts
        """
        if not self.vector_handler:
            logger.error("Vector handler not initialized")
            return
        
        if not self.model:
            logger.error("Model not initialized for embeddings")
            return
        
        logger.info(f"Inserting {len(formatted_data)} documents into vector DB...")
        
        inserted_count = 0
        skipped_count = 0
        
        for data in formatted_data:
            try:
                # Generate embedding
                content = data["content"]
                vector = self.model.get_embedding(content)
                
                # Insert into vector DB
                uuid = self.vector_handler.insert_document(
                    etf_code=data["etf_code"],
                    etf_name=data["etf_name"],
                    content=content,
                    vector=vector,
                    source=data["source"],
                    etf_type=data["etf_type"],
                    category=data.get("category", ""),
                    additional_metadata=data.get("metadata"),
                    check_duplicate=True
                )
                
                if uuid:
                    inserted_count += 1
                else:
                    skipped_count += 1
            
            except Exception as e:
                logger.error(f"Error inserting {data.get('etf_name')}: {e}")
        
        logger.info(
            f"Vector DB insertion complete: "
            f"{inserted_count} inserted, {skipped_count} skipped (duplicates)"
        )


# Example usage
if __name__ == "__main__":
    logger.info("Testing ETF Data Collector...")
    
    try:
        # Initialize components
        vector_handler = WeaviateHandler()
        
        collector = ETFDataCollector(
            vector_handler=vector_handler,
            model_type="local" # openai, local
        )
        
        # Collect all data
        results = collector.collect_all(
            domestic_max=5,  # Test with small number
            foreign_tickers=["SPY", "QQQ", "ARKK"],
            dart_days=30,
            insert_to_db=True
        )
        
        print(f"\nCollection Summary:")
        print(f"  Domestic ETFs: {len(results['domestic'])}")
        print(f"  Foreign ETFs: {len(results['foreign'])}")
        print(f"  DART Disclosures: {len(results['dart'])}")
        print(f"  Total: {results['total']}")
        
        vector_handler.close()
        
    except Exception as e:
        logger.error(f"Error: {e}")

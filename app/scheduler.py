"""
APScheduler-based ETF Data Collection Scheduler
Automatically collects ETF data daily
"""

import json
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.config import get_settings
from app.crawler.collector import ETFDataCollector
from app.vector_store.weaviate_handler import WeaviateHandler
from app.model.model_factory import get_model


class ETFScheduler:
    """Scheduler for automatic ETF data collection"""
    
    def __init__(self):
        """Initialize scheduler"""
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler()
        self.vector_handler = None
        self.collector = None
        
        logger.info("ETF Scheduler initialized")
    
    def initialize_components(self):
        """Initialize vector handler and collector"""
        try:
            logger.info("Initializing scheduler components...")
            
            # Initialize vector handler
            self.vector_handler = WeaviateHandler()
            
            # Initialize collector
            self.collector = ETFDataCollector(
                vector_handler=self.vector_handler,
                model_type=self.settings.llm_provider
            )
            
            logger.info("Scheduler components initialized successfully")
        
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            raise
    
    def collect_etf_data(self):
        """
        Job function: Collect ETF data from all sources
        """
        logger.info("=" * 60)
        logger.info(f"Starting scheduled ETF data collection at {datetime.now()}")
        logger.info("=" * 60)
        
        try:
            if not self.collector:
                self.initialize_components()
            
            # Collect all data (using config settings)
            logger.info(f"Collection limits: Domestic={self.settings.max_domestic_etfs}, Foreign={self.settings.max_foreign_etfs}, DART={self.settings.max_dart_docs}")
            
            results = self.collector.collect_all(
                domestic_max=self.settings.max_domestic_etfs,  # Use config limit
                foreign_tickers=None,  # Use default list
                foreign_max=self.settings.max_foreign_etfs,  # Use config limit
                dart_days=7,  # Last week
                dart_max=self.settings.max_dart_docs,  # Use config limit
                insert_to_db=True,
                only_outdated=self.settings.collect_only_outdated,  # Use config
                days_threshold=self.settings.update_threshold_days  # Use config
            )
            
            # Update metadata
            self._update_metadata(results)
            
            logger.info("=" * 60)
            logger.info(f"Scheduled collection completed successfully")
            logger.info(f"  Domestic: {len(results['domestic'])}")
            logger.info(f"  Foreign: {len(results['foreign'])}")
            logger.info(f"  DART: {len(results['dart'])}")
            logger.info(f"  Total: {results['total']}")
            logger.info("=" * 60)
        
        except Exception as e:
            logger.error(f"Error in scheduled collection: {e}")
            logger.exception(e)
    
    def _update_metadata(self, results: dict):
        """Update metadata file with collection results"""
        try:
            metadata = {
                "last_updated": datetime.now().isoformat(),
                "etf_count": {
                    "domestic": len(results.get("domestic", [])),
                    "foreign": len(results.get("foreign", []))
                },
                "dart_count": len(results.get("dart", [])),
                "total_count": results.get("total", 0),
                "data_sources": {
                    "naver": "https://finance.naver.com",
                    "yfinance": "Yahoo Finance API",
                    "dart": "https://opendart.fss.or.kr"
                }
            }
            
            with open(self.settings.metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Metadata updated: {self.settings.metadata_file}")
        
        except Exception as e:
            logger.error(f"Error updating metadata: {e}")
    
    def add_daily_job(self):
        """Add daily collection job"""
        hour = self.settings.crawl_time_hour
        minute = self.settings.crawl_time_minute
        
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone="Asia/Seoul"
        )
        
        self.scheduler.add_job(
            self.collect_etf_data,
            trigger=trigger,
            id="daily_etf_collection",
            name="Daily ETF Data Collection",
            replace_existing=True
        )
        
        logger.info(f"Scheduled daily collection at {hour:02d}:{minute:02d} KST")
    
    def add_manual_job(self, run_date: datetime = None):
        """
        Add one-time manual collection job
        
        Args:
            run_date: When to run (default: now)
        """
        if run_date is None:
            run_date = datetime.now()
        
        self.scheduler.add_job(
            self.collect_etf_data,
            trigger="date",
            run_date=run_date,
            id=f"manual_collection_{run_date.strftime('%Y%m%d_%H%M%S')}",
            name="Manual ETF Collection"
        )
        
        logger.info(f"Scheduled manual collection at {run_date}")
    
    def start(self, run_immediately: bool = False):
        """
        Start the scheduler
        
        Args:
            run_immediately: Run collection immediately on start
        """
        if not self.settings.enable_scheduler:
            logger.warning("Scheduler is disabled in config")
            return
        
        try:
            # Initialize components
            self.initialize_components()
            
            # Add daily job
            self.add_daily_job()
            
            # Run immediately if requested
            if run_immediately:
                logger.info("Running initial collection...")
                self.collect_etf_data()
            
            # Start scheduler
            self.scheduler.start()
            logger.info("Scheduler started successfully")
            
            # Print next run time
            jobs = self.scheduler.get_jobs()
            if jobs:
                next_run = jobs[0].next_run_time
                logger.info(f"Next scheduled run: {next_run}")
        
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            raise
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
        
        if self.vector_handler:
            self.vector_handler.close()
    
    def get_jobs(self):
        """Get list of scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time),
                "trigger": str(job.trigger)
            })
        return jobs


# Global scheduler instance
_scheduler_instance = None


def get_scheduler() -> ETFScheduler:
    """Get global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ETFScheduler()
    return _scheduler_instance


# Example usage
if __name__ == "__main__":
    import asyncio
    
    logger.info("Testing ETF Scheduler...")
    
    scheduler = ETFScheduler()
    
    try:
        # Start scheduler with immediate run
        scheduler.start(run_immediately=True)
        
        # Print scheduled jobs
        jobs = scheduler.get_jobs()
        print("\nScheduled Jobs:")
        for job in jobs:
            print(f"  - {job['name']}: {job['next_run']}")
        
        # Keep running (in production, this would be handled by the main app)
        print("\nScheduler is running. Press Ctrl+C to stop...")
        asyncio.get_event_loop().run_forever()
    
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.stop()
    
    except Exception as e:
        logger.error(f"Error: {e}")
        scheduler.stop()

"""
Full ETF Data Collection Script
Collects ALL ETF data without limits and inserts into Weaviate using OpenAI embeddings
Usage: python collect_all_data.py [--domestic-only] [--foreign-only] [--dart-only]
nohup python collect_all_data.py --all-popular-foreign > collection.out 2>&1 &
"""

import sys
import argparse
from datetime import datetime
from loguru import logger

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/collection_{time}.log",
    rotation="100 MB",
    retention="30 days",
    level="DEBUG"
)


def main():
    """Main collection function"""
    
    parser = argparse.ArgumentParser(description="Collect all ETF data into Weaviate")
    parser.add_argument("--domestic-only", action="store_true", help="Only collect domestic ETFs")
    parser.add_argument("--foreign-only", action="store_true", help="Only collect foreign ETFs")
    parser.add_argument("--dart-only", action="store_true", help="Only collect DART disclosures")
    parser.add_argument("--domestic-max", type=int, default=None, help="Max domestic ETFs (default: no limit)")
    parser.add_argument("--foreign-max", type=int, default=None, help="Max foreign ETFs (default: no limit)")
    parser.add_argument("--dart-max", type=int, default=None, help="Max DART docs (default: no limit)")
    parser.add_argument("--dart-days", type=int, default=30, help="DART lookback days (default: 30)")
    parser.add_argument("--skip-outdated-check", action="store_true", help="Collect all ETFs regardless of update date")
    parser.add_argument("--days-threshold", type=int, default=7, help="Days threshold for outdated check (default: 7)")
    parser.add_argument("--model", type=str, default="openai", choices=["openai", "local"], help="Model type (default: openai)")
    parser.add_argument("--foreign-tickers-file", type=str, default=None, help="File with foreign ETF tickers (one per line)")
    parser.add_argument("--all-popular-foreign", action="store_true", help="Collect all popular foreign ETFs (expanded list ~200 ETFs)")
    parser.set_defaults(domestic_only=True, foreign_only=False, dart_only=False)
    args = parser.parse_args()
    
    print("=" * 80)
    print("ETF Data Collection - Full Mode")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Step 1: Check configuration
    print("\n[Step 1/5] Checking configuration...")
    try:
        from app.config import get_settings, validate_config
        settings = get_settings()
        validate_config()
        
        logger.info(f"✓ LLM Provider: {args.model}")
        logger.info(f"✓ Weaviate URL: {settings.weaviate_url}")
        
        if args.model == "openai":
            if not settings.openai_api_key:
                logger.error("✗ OPENAI_API_KEY not set in environment")
                logger.info("Please set OPENAI_API_KEY in your .env file or environment")
                return
            logger.info(f"✓ OpenAI Model: {settings.openai_model}")
            logger.info(f"✓ OpenAI Embedding Model: {settings.openai_embedding_model}")
        else:
            logger.info(f"✓ Local Model: {settings.local_model_type}")
            logger.info(f"✓ Ollama URL: {settings.ollama_base_url}")
            
    except Exception as e:
        logger.error(f"✗ Configuration error: {e}")
        logger.info("Please check your .env file")
        return
    
    # Step 2: Test Weaviate connection
    print("\n[Step 2/5] Testing Weaviate connection...")
    handler = None
    try:
        from app.vector_store.weaviate_handler import WeaviateHandler
        handler = WeaviateHandler()
        count = handler.get_document_count()
        logger.info(f"✓ Connected to Weaviate")
        logger.info(f"✓ Current document count: {count:,}")
        
        # Get collection info
        try:
            collection = handler.client.collections.get(settings.weaviate_class_name)
            logger.info(f"✓ Collection exists: {settings.weaviate_class_name}")
        except Exception as e:
            logger.warning(f"Could not verify collection: {e}")
        
    except Exception as e:
        logger.error(f"✗ Weaviate connection failed: {e}")
        logger.info("Please check your Weaviate connection:")
        logger.info(f"  - URL: {settings.weaviate_url}")
        logger.info("  - For local: docker-compose up -d")
        logger.info("  - For cloud: check API key and URL")
        if handler:
            handler.close()
        return
    
    # Step 3: Test LLM model
    print("\n[Step 3/5] Testing LLM model...")
    try:
        from app.model.model_factory import get_model
        model = get_model(args.model)
        logger.info(f"✓ LLM model loaded: {type(model).__name__}")
        
        # Test embedding
        test_text = "Test embedding"
        embedding = model.get_embedding(test_text)
        logger.info(f"✓ Embedding test successful (dim: {len(embedding)})")
        
    except Exception as e:
        logger.error(f"✗ LLM model error: {e}")
        logger.info("Please check your API keys and model configuration")
        if handler:
            handler.close()
        return
    
    # Step 4: Initialize collector
    print("\n[Step 4/5] Initializing data collector...")
    try:
        from app.crawler.collector import ETFDataCollector
        
        collector = ETFDataCollector(
            vector_handler=handler,
            model_type=args.model
        )
        logger.info("✓ ETF Data Collector initialized")
        
    except Exception as e:
        logger.error(f"✗ Collector initialization failed: {e}")
        return
    
    # Step 5: Collect data
    print("\n[Step 5/5] Collecting ETF data...")
    print("-" * 80)
    
    collection_mode = []
    if args.domestic_only:
        collection_mode.append("domestic")
    if args.foreign_only:
        collection_mode.append("foreign")
    if args.dart_only:
        collection_mode.append("DART")
    
    if not collection_mode:
        collection_mode = ["domestic", "foreign", "DART"]
    
    logger.info(f"📊 Collection mode: {', '.join(collection_mode)}")
    logger.info(f"📊 Model: {args.model}")
    
    if not args.skip_outdated_check:
        logger.info(f"📅 Only collecting data older than {args.days_threshold} days")
    else:
        logger.info(f"📅 Collecting ALL data (no date filtering)")
    
    if args.domestic_max:
        logger.info(f"🔢 Domestic limit: {args.domestic_max}")
    else:
        logger.info(f"🔢 Domestic limit: NO LIMIT (collecting all)")
        
    if args.foreign_max:
        logger.info(f"🔢 Foreign limit: {args.foreign_max}")
    else:
        logger.info(f"🔢 Foreign limit: NO LIMIT (collecting all)")
        
    if args.dart_max:
        logger.info(f"🔢 DART limit: {args.dart_max}")
    else:
        logger.info(f"🔢 DART limit: NO LIMIT (collecting all)")
    
    print("-" * 80)
    print("\n⚠️  This may take a LONG time depending on the number of ETFs.")
    print("⚠️  Press Ctrl+C to stop at any time.\n")
    
    try:
        start_time = datetime.now()
        
        results = {
            "domestic": [],
            "foreign": [],
            "dart": [],
            "total": 0
        }
        
        # Collect based on mode
        if "domestic" in collection_mode:
            logger.info("🇰🇷 Starting domestic ETF collection...")
            try:
                domestic = collector.collect_domestic_etfs(
                    max_items=args.domestic_max,
                    insert_to_db=True,
                    only_outdated=not args.skip_outdated_check,
                    days_threshold=args.days_threshold
                )
                results["domestic"] = domestic
                logger.info(f"✓ Collected {len(domestic)} domestic ETFs")
            except Exception as e:
                logger.error(f"✗ Domestic collection error: {e}")
        
        if "foreign" in collection_mode:
            logger.info("🇺🇸 Starting foreign ETF collection...")
            try:
                # Determine which tickers to use
                if args.foreign_tickers_file:
                    # Load from file
                    logger.info(f"Loading tickers from file: {args.foreign_tickers_file}")
                    with open(args.foreign_tickers_file, 'r') as f:
                        popular_tickers = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    logger.info(f"Loaded {len(popular_tickers)} tickers from file")
                    
                elif args.all_popular_foreign:
                    # Extended list of ~200 popular US ETFs
                    popular_tickers = [
                        # === Broad Market Index ETFs ===
                        # S&P 500
                        "SPY", "VOO", "IVV", "SPLG", "SPYG", "SPYV",
                        # Nasdaq
                        "QQQ", "QQQM", "QQEW", "QQQJ",
                        # Russell
                        "IWM", "IWN", "IWO", "VTWO", "VTWG", "VTWV",
                        # Dow Jones
                        "DIA", "UDOW", "SDOW",
                        # Total Market
                        "VTI", "ITOT", "SPTM", "SCHB",
                        # Mid Cap
                        "IJH", "MDY", "VO", "IVOO",
                        # Large Cap
                        "VV", "OEF", "SCHX", "ILCB",
                        
                        # === Sector ETFs ===
                        # Technology
                        "XLK", "VGT", "FTEC", "IYW", "IGV", "SOXX", "SMH", "XSD",
                        # Financial
                        "XLF", "VFH", "KBWB", "IAT", "KRE",
                        # Healthcare
                        "XLV", "VHT", "IYH", "IBB", "XBI", "IHI",
                        # Consumer Discretionary
                        "XLY", "VCR", "FDIS", "IYC", "RTH",
                        # Consumer Staples
                        "XLP", "VDC", "FSTA", "IYK",
                        # Energy
                        "XLE", "VDE", "IYE", "XOP", "OIH", "ICLN", "TAN", "PBW",
                        # Materials
                        "XLB", "VAW", "IYM",
                        # Industrials
                        "XLI", "VIS", "IYJ",
                        # Utilities
                        "XLU", "VPU", "IDU",
                        # Real Estate
                        "XLRE", "VNQ", "IYR", "SCHH",
                        # Communication Services
                        "XLC", "VOX",
                        
                        # === International ETFs ===
                        # Developed Markets
                        "EFA", "VEA", "IEFA", "SCHF", "IXUS", "VEU",
                        # Emerging Markets
                        "EEM", "VWO", "IEMG", "SCHE", "SPEM", "DEM", "EEMV",
                        # Asia Pacific
                        "AAXJ", "VPL", "EPP",
                        # Europe
                        "VGK", "EZU", "FEZ", "HEDJ",
                        # China
                        "FXI", "MCHI", "ASHR", "KWEB", "CQQQ",
                        # Japan
                        "EWJ", "DXJ", "DBJP",
                        # India
                        "INDA", "EPI", "INDY",
                        # Latin America
                        "ILF", "EWZ", "ARGT",
                        
                        # === Growth & Value ===
                        # Growth
                        "VUG", "VOOG", "IVW", "SCHG", "SPYG", "IWF",
                        # Value
                        "VTV", "VOOV", "IVE", "SCHV", "SPYV", "IWD",
                        # Dividend
                        "VIG", "SCHD", "DVY", "VYM", "DGRO", "SDY", "HDV", "NOBL",
                        
                        # === Thematic & Innovation ===
                        # ARK ETFs
                        "ARKK", "ARKW", "ARKG", "ARKF", "ARKQ", "ARKX", "IZRL",
                        # Clean Energy
                        "ICLN", "TAN", "PBW", "QCLN", "ACES",
                        # Cloud Computing
                        "SKYY", "CLOU", "WFH",
                        # Cybersecurity
                        "HACK", "CIBR", "BUG",
                        # Robotics & AI
                        "BOTZ", "ROBO", "IRBO", "AIQ",
                        # EV & Batteries
                        "LIT", "BATT", "DRIV", "IDRV",
                        # Cannabis
                        "MJ", "YOLO", "CNBS",
                        # Gaming
                        "ESPO", "HERO", "BJK",
                        # Space
                        "UFO", "ARKX",
                        
                        # === Leveraged ETFs ===
                        # 2x Long
                        "SSO", "QLD", "UWM", "UYG", "URE",
                        # 3x Long
                        "UPRO", "TQQQ", "UDOW", "TNA", "TECL", "SOXL",
                        # Inverse
                        "SH", "PSQ", "RWM", "DOG",
                        # 2x Inverse
                        "SDS", "QID", "TWM",
                        # 3x Inverse
                        "SPXU", "SQQQ", "SDOW", "TZA",
                        
                        # === Fixed Income (Bonds) ===
                        # Aggregate
                        "AGG", "BND", "BNDX", "SCHZ", "IAGG",
                        # Treasury
                        "TLT", "IEF", "SHY", "IEI", "SHV", "GOVT", "VGIT", "VGLT",
                        # Corporate
                        "LQD", "VCIT", "VCSH", "USIG", "IGLB",
                        # High Yield
                        "HYG", "JNK", "SHYG", "SJNK", "ANGL",
                        # International Bonds
                        "BNDX", "IAGG", "EMB", "PCY",
                        # TIPS
                        "TIP", "VTIP", "SCHP", "STIP",
                        # Municipal
                        "MUB", "VTEB", "TFI", "SUB",
                        
                        # === Commodities ===
                        # Gold
                        "GLD", "IAU", "GLDM", "BAR", "SGOL",
                        # Silver
                        "SLV", "SIVR",
                        # Oil & Gas
                        "USO", "UNG", "BNO", "OIL",
                        # Broad Commodities
                        "DBC", "GSG", "PDBC", "COMT",
                        # Agriculture
                        "DBA", "CORN", "WEAT", "SOYB",
                        # Metals
                        "DBB", "PICK", "COPX",
                        
                        # === Alternative & Others ===
                        # Volatility
                        "VXX", "UVXY", "SVXY", "VIXY",
                        # Bitcoin & Crypto
                        "BITO", "BTF", "GBTC",
                        # Multi-Asset
                        "AOR", "AOA", "AOM",
                    ]
                    logger.info(f"Using extended popular list: {len(popular_tickers)} ETFs")
                    
                else:
                    # Default minimal list (~40 ETFs)
                    popular_tickers = [
                        # Major Index ETFs
                        "SPY", "VOO", "IVV",  # S&P 500
                        "QQQ", "VGT", "XLK",  # Tech/Nasdaq
                        "DIA", "VTI", "ITOT", # Dow/Total Market
                        # Sector ETFs
                        "XLF", "XLE", "XLV", "XLP", "XLI", "XLB", "XLU", "XLRE", "XLC",
                        # Bond ETFs
                        "AGG", "BND", "TLT", "IEF", "SHY",
                        # International
                        "EFA", "VEA", "IEFA", "EEM", "VWO",
                        # Thematic
                        "ARKK", "ARKW", "ARKG", "ICLN", "TAN", "LIT",
                        # Gold/Commodities
                        "GLD", "SLV", "USO", "DBC",
                    ]
                    logger.info(f"Using default minimal list: {len(popular_tickers)} ETFs")
                
                foreign = collector.collect_foreign_etfs(
                    tickers=popular_tickers,
                    insert_to_db=True,
                    max_items=args.foreign_max
                )
                results["foreign"] = foreign
                logger.info(f"✓ Collected {len(foreign)} foreign ETFs")
            except Exception as e:
                logger.error(f"✗ Foreign collection error: {e}")
        
        if "DART" in collection_mode:
            logger.info("📄 Starting DART disclosure collection...")
            try:
                dart = collector.collect_dart_disclosures(
                    days=args.dart_days,
                    insert_to_db=True,
                    max_items=args.dart_max
                )
                results["dart"] = dart
                logger.info(f"✓ Collected {len(dart)} DART disclosures")
            except Exception as e:
                logger.error(f"✗ DART collection error: {e}")
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Calculate totals
        total_collected = len(results["domestic"]) + len(results["foreign"]) + len(results["dart"])
        
        # Get final count from DB
        final_count = handler.get_document_count()
        
        # Close handler
        handler.close()
        
        # Print summary
        print("\n" + "=" * 80)
        print("Collection Summary")
        print("=" * 80)
        print(f"Start Time:      {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time:        {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration:        {duration}")
        print("-" * 80)
        print(f"Domestic ETFs:   {len(results['domestic']):>6,}")
        print(f"Foreign ETFs:    {len(results['foreign']):>6,}")
        print(f"DART Docs:       {len(results['dart']):>6,}")
        print("-" * 80)
        print(f"Total Collected: {total_collected:>6,}")
        print(f"DB Total:        {final_count:>6,}")
        print("=" * 80)
        
        logger.info("✅ Collection completed successfully!")
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Collection interrupted by user")
        logger.info("Partial data may have been inserted into the database")
        handler.close()
        return
    except Exception as e:
        logger.error(f"✗ Collection failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        handler.close()
        return


if __name__ == "__main__":
    main()

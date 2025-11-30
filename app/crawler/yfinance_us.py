"""
Yahoo Finance ETF Crawler (using yfinance)
Crawls foreign ETF information
"""

from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import yfinance as yf
from loguru import logger


def load_tickers_from_file(file_path: str) -> List[str]:
    """
    Load ETF tickers from a text file.
    Lines starting with # are treated as comments.
    Empty lines are ignored.
    
    Args:
        file_path: Path to the ticker file
        
    Returns:
        List of ticker symbols
    """
    tickers = []
    path = Path(file_path)
    
    if not path.exists():
        logger.warning(f"Ticker file not found: {file_path}")
        return tickers
    
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Take only the first word (in case of inline comments)
            ticker = line.split()[0].upper()
            if ticker:
                tickers.append(ticker)
    
    logger.info(f"Loaded {len(tickers)} tickers from {file_path}")
    return tickers


class YFinanceETFCrawler:
    """Crawler for foreign ETF data using yfinance"""
    
    # Popular US ETFs to track
    DEFAULT_ETF_TICKERS = [
        # Broad Market - Large Cap
        "SPY",    # S&P 500 (SPDR)
        "VOO",    # S&P 500 (Vanguard)
        "IVV",    # S&P 500 (iShares)
        "QQQ",    # Nasdaq 100
        "QQQM",   # Nasdaq 100 (Mini, lower expense ratio)
        "IWM",    # Russell 2000
        "IWB",    # Russell 1000
        "DIA",    # Dow Jones
        "VTI",    # Total Stock Market
        "ITOT",   # Total Stock Market (iShares)
        "VT",     # Total World Stock
        "VXUS",   # Total International
        
        # Growth & Value
        "VUG",    # Vanguard Growth
        "VTV",    # Vanguard Value
        "IWF",    # Russell 1000 Growth
        "IWD",    # Russell 1000 Value
        "SCHG",   # Schwab US Large-Cap Growth
        "SCHD",   # Schwab US Dividend Equity
        
        # Tech & Innovation
        "ARKK",   # ARK Innovation
        "ARKW",   # ARK Next Gen Internet
        "ARKG",   # ARK Genomic Revolution
        "ARKF",   # ARK Fintech Innovation
        "SOXL",   # Semiconductor 3x Bull
        "SOXX",   # Semiconductor
        "SMH",    # Semiconductor (VanEck)
        "TQQQ",   # Nasdaq 100 3x Bull
        "IGV",    # Software
        "WCLD",   # Cloud Computing
        "BOTZ",   # Robotics & AI
        "ROBO",   # Global Robotics & Automation
        "AIQ",    # AI & Big Data
        
        # International
        "EFA",    # EAFE (Developed Markets)
        "EEM",    # Emerging Markets
        "VWO",    # Emerging Markets (Vanguard)
        "IEMG",   # Core Emerging Markets
        "FXI",    # China Large-Cap
        "KWEB",   # China Internet
        "MCHI",   # China
        "EWJ",    # Japan
        "EWY",    # South Korea
        "EWT",    # Taiwan
        "INDA",   # India
        "EWZ",    # Brazil
        "VEA",    # Developed Markets
        
        # Sector ETFs
        "XLF",    # Financial
        "XLE",    # Energy
        "XLK",    # Technology
        "XLV",    # Healthcare
        "XLI",    # Industrial
        "XLY",    # Consumer Discretionary
        "XLP",    # Consumer Staples
        "XLU",    # Utilities
        "XLRE",   # Real Estate
        "XLB",    # Materials
        "XLC",    # Communication Services
        
        # Thematic
        "ICLN",   # Clean Energy
        "TAN",    # Solar
        "LIT",    # Lithium & Battery
        "DRIV",   # Electric Vehicles
        "JETS",   # Airlines
        "IBB",    # Biotech
        "XBI",    # Biotech (SPDR)
        "ARKG",   # Genomics
        "HACK",   # Cybersecurity
        "CIBR",   # Cybersecurity
        
        # Bond ETFs
        "AGG",    # Total Bond Market
        "BND",    # Total Bond Market (Vanguard)
        "TLT",    # 20+ Year Treasury
        "IEF",    # 7-10 Year Treasury
        "SHY",    # 1-3 Year Treasury
        "TIP",    # TIPS
        "LQD",    # Investment Grade Corporate
        "HYG",    # High Yield Corporate
        "JNK",    # High Yield Corporate (SPDR)
        "EMB",    # Emerging Markets Bond
        "BNDX",   # International Bond
        
        # Commodity
        "GLD",    # Gold (SPDR)
        "IAU",    # Gold (iShares)
        "SLV",    # Silver
        "USO",    # Oil
        "UNG",    # Natural Gas
        "DBA",    # Agriculture
        "DBC",    # Commodity Index
        "PDBC",   # Optimum Yield Diversified Commodity
        
        # Real Estate
        "VNQ",    # Vanguard Real Estate
        "SCHH",   # Schwab US REIT
        "IYR",    # iShares US Real Estate
        "VNQI",   # International Real Estate
        
        # Dividend & Income
        "VYM",    # Vanguard High Dividend
        "DVY",    # Select Dividend
        "HDV",    # Core High Dividend
        "SPHD",   # S&P 500 High Dividend Low Volatility
        "JEPI",   # JPMorgan Equity Premium Income
        "JEPQ",   # JPMorgan Nasdaq Equity Premium Income
        
        # Leveraged & Inverse
        "VIXY",   # Volatility
        "UVXY",   # Ultra Volatility
        "SQQQ",   # Nasdaq 100 -3x
        "SPXU",   # S&P 500 -3x
        "SPXL",   # S&P 500 3x
        "UPRO",   # S&P 500 3x (ProShares)
        "QLD",    # Nasdaq 100 2x
        "SSO",    # S&P 500 2x
        "SH",     # S&P 500 -1x
        "PSQ",    # Nasdaq 100 -1x
        "SOXS",   # Semiconductor -3x
        
        # Low Volatility & Quality
        "USMV",   # Min Volatility USA
        "QUAL",   # Quality Factor
        "MTUM",   # Momentum Factor
        "SIZE",   # Size Factor
        "VLUE",   # Value Factor
    ]
    
    # Default ticker file path
    DEFAULT_TICKER_FILE = "data/us_etf_comprehensive.txt"
    
    def __init__(self, custom_tickers: Optional[List[str]] = None, ticker_file: Optional[str] = None):
        """
        Initialize yfinance crawler
        
        Args:
            custom_tickers: Custom list of ticker symbols (highest priority)
            ticker_file: Path to file containing ticker symbols (second priority)
                        If not provided, tries DEFAULT_TICKER_FILE first,
                        then falls back to DEFAULT_ETF_TICKERS
        """
        if custom_tickers:
            self.tickers = custom_tickers
            logger.info(f"YFinance Crawler initialized with {len(self.tickers)} custom tickers")
        elif ticker_file:
            self.tickers = load_tickers_from_file(ticker_file)
            if not self.tickers:
                logger.warning(f"No tickers loaded from {ticker_file}, using defaults")
                self.tickers = self.DEFAULT_ETF_TICKERS
        else:
            # Try to load from default file first
            default_file = Path(self.DEFAULT_TICKER_FILE)
            if default_file.exists():
                self.tickers = load_tickers_from_file(self.DEFAULT_TICKER_FILE)
                if not self.tickers:
                    self.tickers = self.DEFAULT_ETF_TICKERS
            else:
                self.tickers = self.DEFAULT_ETF_TICKERS
                logger.info(f"Using {len(self.tickers)} default tickers (file not found: {self.DEFAULT_TICKER_FILE})")
    
    def get_etf_info(self, ticker: str) -> Optional[Dict[str, any]]:
        """
        Get comprehensive info for a single ETF
        
        Args:
            ticker: ETF ticker symbol
        
        Returns:
            ETF info dict or None if failed
        """
        try:
            logger.debug(f"Fetching info for {ticker}")
            
            etf = yf.Ticker(ticker)
            info = etf.info
            
            if not info or len(info) < 5:
                logger.warning(f"No valid data for {ticker}")
                return None
            
            # Extract key information
            detail = {
                "ticker": ticker,
                "name": info.get("longName", info.get("shortName", ticker)),
                "description": info.get("longBusinessSummary", ""),
                "category": info.get("category", ""),
                "total_assets": info.get("totalAssets", 0),
                "nav": info.get("navPrice", 0),
                "price": info.get("regularMarketPrice", 0),
                "previous_close": info.get("previousClose", 0),
                "year_high": info.get("fiftyTwoWeekHigh", 0),
                "year_low": info.get("fiftyTwoWeekLow", 0),
                "ytd_return": info.get("ytdReturn", 0),
                "beta": info.get("beta3Year", 0),
                "expense_ratio": info.get("annualReportExpenseRatio", 0),
                "yield": info.get("yield", info.get("trailingAnnualDividendYield", 0)),
                "inception_date": info.get("fundInceptionDate", ""),
                "fund_family": info.get("fundFamily", ""),
                "currency": info.get("currency", "USD"),
                "exchange": info.get("exchange", ""),
                "crawl_date": datetime.now().isoformat(),
                "source": "yfinance"
            }
            
            # Get top holdings if available
            try:
                holdings = etf.major_holders
                if holdings is not None and not holdings.empty:
                    detail["major_holders"] = holdings.to_dict()
            except:
                pass
            
            logger.debug(f"Successfully fetched info for {ticker}")
            return detail
        
        except Exception as e:
            logger.error(f"Error fetching {ticker}: {e}")
            return None
    
    def get_all_etf_info(
        self,
        tickers: Optional[List[str]] = None
    ) -> List[Dict[str, any]]:
        """
        Get info for multiple ETFs
        
        Args:
            tickers: List of tickers (uses default if None)
        
        Returns:
            List of ETF info dicts
        """
        tickers = tickers or self.tickers
        logger.info(f"Fetching info for {len(tickers)} ETFs...")
        
        results = []
        for i, ticker in enumerate(tickers, 1):
            logger.info(f"[{i}/{len(tickers)}] Fetching {ticker}")
            
            info = self.get_etf_info(ticker)
            if info:
                results.append(info)
        
        logger.info(f"Successfully fetched {len(results)}/{len(tickers)} ETFs")
        return results
    
    def get_etf_historical_data(
        self,
        ticker: str,
        period: str = "1mo"
    ) -> Optional[Dict[str, any]]:
        """
        Get historical price data
        
        Args:
            ticker: ETF ticker
            period: Period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        
        Returns:
            Historical data dict
        """
        try:
            etf = yf.Ticker(ticker)
            hist = etf.history(period=period)
            
            if hist.empty:
                return None
            
            return {
                "ticker": ticker,
                "period": period,
                "data": hist.to_dict(),
                "start_date": str(hist.index[0]),
                "end_date": str(hist.index[-1]),
                "num_records": len(hist)
            }
        
        except Exception as e:
            logger.error(f"Error fetching historical data for {ticker}: {e}")
            return None
    
    def format_for_vector_db(
        self,
        etf_info: Dict[str, any]
    ) -> Dict[str, any]:
        """
        Format ETF info for vector database insertion
        
        Args:
            etf_info: Raw ETF info dict
        
        Returns:
            Formatted dict ready for vector DB
        """
        # Create rich text content
        ticker = etf_info.get("ticker", "")
        name = etf_info.get("name", "")
        description = etf_info.get("description", "")
        
        content_parts = [
            f"ETF 이름: {name}",
            f"티커: {ticker}",
            f"카테고리: {etf_info.get('category', 'N/A')}",
            f"펀드 제공사: {etf_info.get('fund_family', 'N/A')}",
            f"\n현재가: ${etf_info.get('price', 0):.2f}",
            f"NAV: ${etf_info.get('nav', 0):.2f}",
            f"총 자산: ${etf_info.get('total_assets', 0):,.0f}",
            f"보수율: {etf_info.get('expense_ratio', 0) * 100:.2f}%",
            f"배당수익률: {etf_info.get('yield', 0) * 100:.2f}%",
            f"베타: {etf_info.get('beta', 0):.2f}",
            f"52주 최고가: ${etf_info.get('year_high', 0):.2f}",
            f"52주 최저가: ${etf_info.get('year_low', 0):.2f}",
        ]
        
        if description:
            content_parts.append(f"\n설명: {description}")
        
        content = "\n".join(content_parts)
        
        return {
            "etf_code": ticker,
            "etf_name": name,
            "content": content,
            "source": "yfinance",
            "etf_type": "foreign",
            "category": etf_info.get("category", ""),
            "metadata": {
                "ticker": ticker,
                "price": etf_info.get("price"),
                "nav": etf_info.get("nav"),
                "total_assets": etf_info.get("total_assets"),
                "expense_ratio": etf_info.get("expense_ratio"),
                "yield": etf_info.get("yield"),
                "beta": etf_info.get("beta"),
                "fund_family": etf_info.get("fund_family"),
                "exchange": etf_info.get("exchange"),
                "currency": etf_info.get("currency"),
                "description": description[:500],  # Truncate for metadata
            }
        }


# Example usage
if __name__ == "__main__":
    logger.info("Testing YFinance ETF Crawler...")
    
    crawler = YFinanceETFCrawler()
    
    # Test: Get info for a few ETFs
    test_tickers = ["SPY", "QQQ", "ARKK"]
    etfs = crawler.get_all_etf_info(test_tickers)
    
    print(f"\nFetched {len(etfs)} ETFs")
    
    for etf in etfs:
        print(f"\n{etf['name']} ({etf['ticker']})")
        print(f"  Price: ${etf['price']:.2f}")
        print(f"  Expense Ratio: {etf['expense_ratio'] * 100:.2f}%")
        print(f"  Description: {etf['description'][:100]}...")
        
        # Format for vector DB
        formatted = crawler.format_for_vector_db(etf)
        print(f"\n  Formatted content preview:")
        print(f"  {formatted['content'][:150]}...")

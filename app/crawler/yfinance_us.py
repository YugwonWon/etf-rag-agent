"""
Yahoo Finance ETF Crawler (using yfinance)
Crawls foreign ETF information
"""

from typing import List, Dict, Optional
from datetime import datetime
import yfinance as yf
from loguru import logger


class YFinanceETFCrawler:
    """Crawler for foreign ETF data using yfinance"""
    
    # Popular US ETFs to track
    DEFAULT_ETF_TICKERS = [
        # Broad Market
        "SPY",    # S&P 500
        "QQQ",    # Nasdaq 100
        "IWM",    # Russell 2000
        "DIA",    # Dow Jones
        "VTI",    # Total Stock Market
        
        # Tech & Growth
        "ARKK",   # ARK Innovation
        "ARKW",   # ARK Next Gen Internet
        "ARKG",   # ARK Genomic Revolution
        "SOXL",   # Semiconductor 3x
        "TQQQ",   # Nasdaq 100 3x
        
        # International
        "EFA",    # EAFE (Developed Markets)
        "EEM",    # Emerging Markets
        "VWO",    # Emerging Markets
        "FXI",    # China Large-Cap
        
        # Sector ETFs
        "XLF",    # Financial
        "XLE",    # Energy
        "XLK",    # Technology
        "XLV",    # Healthcare
        "XLI",    # Industrial
        
        # Bond ETFs
        "AGG",    # Total Bond Market
        "TLT",    # 20+ Year Treasury
        "HYG",    # High Yield Corporate
        
        # Commodity
        "GLD",    # Gold
        "SLV",    # Silver
        "USO",    # Oil
        
        # Inverse & Volatility
        "VIXY",   # Volatility
        "SQQQ",   # Nasdaq 100 -3x
    ]
    
    def __init__(self, custom_tickers: Optional[List[str]] = None):
        """
        Initialize yfinance crawler
        
        Args:
            custom_tickers: Custom list of ticker symbols
        """
        self.tickers = custom_tickers or self.DEFAULT_ETF_TICKERS
        logger.info(f"YFinance Crawler initialized with {len(self.tickers)} tickers")
    
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

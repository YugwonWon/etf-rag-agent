"""
Naver Finance ETF Crawler
Crawls domestic ETF information from Naver Finance
"""

import re
import time
from typing import List, Dict, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from loguru import logger
import pandas as pd


class NaverETFCrawler:
    """Crawler for Naver Finance ETF data"""
    
    def __init__(self):
        """Initialize crawler"""
        self.base_url = "https://finance.naver.com"
        # Use API endpoint instead of HTML page (1033 ETFs available)
        self.etf_list_url = f"{self.base_url}/api/sise/etfItemList.nhn"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        logger.info("Naver ETF Crawler initialized")
    
    def get_etf_list(self) -> List[Dict[str, str]]:
        """
        Get list of all domestic ETFs from Naver Finance API
        
        Returns:
            List of ETF info dicts with code, name, etc.
        """
        try:
            logger.info("Fetching ETF list from Naver Finance API...")
            
            # Add timeout to prevent hanging (10s connect, 30s read)
            response = requests.get(
                self.etf_list_url, 
                headers=self.headers,
                timeout=(10, 30)
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('resultCode') != 'success':
                logger.error(f"API returned non-success: {data.get('resultCode')}")
                return []
            
            result = data.get('result', {})
            etf_list = result.get('etfItemList', [])
            
            if not etf_list:
                logger.error("No ETF data in API response")
                return []
            
            etfs = []
            for item in etf_list:
                try:
                    code = item.get('itemcode', '')
                    name = item.get('itemname', '')
                    price = item.get('nowVal', 0)
                    change_rate = item.get('changeRate', 0.0)
                    nav = item.get('nav', 0.0)
                    volume = item.get('quant', 0)
                    
                    if not code or not name:
                        continue
                    
                    etf_info = {
                        "code": code,
                        "name": name,
                        "price": str(price),
                        "change_rate": f"{change_rate}%",
                        "nav": str(nav),
                        "volume": str(volume),
                        "url": f"{self.base_url}/item/main.naver?code={code}"
                    }
                    
                    etfs.append(etf_info)
                
                except Exception as e:
                    logger.debug(f"Error parsing ETF item: {e}")
                    continue
            
            logger.info(f"Found {len(etfs)} ETFs")
            return etfs
        
        except Exception as e:
            logger.error(f"Error fetching ETF list: {e}")
            return []
    
    def get_etf_detail(self, code: str) -> Optional[Dict[str, any]]:
        """
        Get detailed information for a specific ETF
        
        Args:
            code: ETF code
        
        Returns:
            ETF detail dict
        """
        try:
            url = f"{self.base_url}/item/main.naver?code={code}"
            logger.debug(f"Fetching detail for {code}")
            
            # Add timeout to prevent hanging
            response = requests.get(url, headers=self.headers, timeout=(10, 30))
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract basic info
            summary = soup.find("div", class_="wrap_company")
            name = summary.find("h2").text.strip() if summary and summary.find("h2") else "Unknown"
            
            # Extract current price
            price_elem = soup.find("p", class_="no_today")
            if price_elem:
                price_span = price_elem.find("span", class_="blind")
                price = price_span.text.strip().replace(',', '') if price_span else "N/A"
            else:
                price = "N/A"
            
            # Extract description
            description_div = soup.find("div", class_="description")
            description = description_div.text.strip() if description_div else ""
            
            # Extract key info table
            info_table = soup.find("table", class_="lwidth")
            info_dict = {}
            
            if info_table:
                rows = info_table.find_all("tr")
                for row in rows:
                    ths = row.find_all("th")
                    tds = row.find_all("td")
                    
                    for th, td in zip(ths, tds):
                        key = th.text.strip()
                        value = td.text.strip()
                        info_dict[key] = value
            
            # Extract NAV
            nav_elem = soup.find("em", id="_nav")
            nav = nav_elem.text.strip() if nav_elem else "N/A"
            
            detail = {
                "code": code,
                "name": name,
                "price": price,
                "description": description,
                "nav": nav,
                "info": info_dict,
                "crawl_date": datetime.now().isoformat(),
                "source": "naver_finance"
            }
            
            logger.debug(f"Successfully fetched detail for {code}")
            return detail
        
        except Exception as e:
            logger.error(f"Error fetching detail for {code}: {e}")
            return None
    
    def get_all_etf_details(
        self,
        max_items: Optional[int] = None,
        delay: float = 0.5
    ) -> List[Dict[str, any]]:
        """
        Get detailed info for all ETFs
        
        Args:
            max_items: Maximum number of ETFs to fetch (None for all)
            delay: Delay between requests in seconds
        
        Returns:
            List of ETF detail dicts
        """
        etf_list = self.get_etf_list()
        
        if max_items:
            etf_list = etf_list[:max_items]
        
        logger.info(f"Fetching details for {len(etf_list)} ETFs...")
        
        details = []
        for i, etf in enumerate(etf_list, 1):
            code = etf["code"]
            logger.info(f"[{i}/{len(etf_list)}] Fetching {etf['name']} ({code})")
            
            detail = self.get_etf_detail(code)
            if detail:
                # Merge list info with detail
                detail.update({
                    "price": etf.get("price"),
                    "change": etf.get("change"),
                    "volume": etf.get("volume"),
                })
                details.append(detail)
            
            # Rate limiting
            time.sleep(delay)
        
        logger.info(f"Successfully fetched {len(details)} ETF details")
        return details
    
    def format_for_vector_db(
        self,
        etf_detail: Dict[str, any]
    ) -> Dict[str, any]:
        """
        Format ETF detail for vector database insertion
        
        Args:
            etf_detail: Raw ETF detail dict
        
        Returns:
            Formatted dict ready for vector DB
        """
        # Get info table data
        info = etf_detail.get('info', {})
        
        # NAV 찾기: info 테이블에서 'NAV'로 시작하는 키 찾기
        nav_value = etf_detail.get('nav', 'N/A')
        for key, value in info.items():
            if key.startswith('NAV'):
                nav_value = value
                break
        
        # Create rich text content
        content_parts = [
            f"ETF 이름: {etf_detail.get('name', 'N/A')}",
            f"ETF 코드: {etf_detail.get('code', 'N/A')}",
            f"현재가: {etf_detail.get('price', 'N/A')}원",
            f"NAV: {nav_value}원",
            f"\n설명: {etf_detail.get('description', 'N/A')}",
        ]
        
        # Add info table data (NAV 제외)
        if info:
            content_parts.append("\n상세 정보:")
            for key, value in info.items():
                if not key.startswith('NAV'):  # NAV는 이미 위에 표시
                    content_parts.append(f"- {key}: {value}")
        
        content = "\n".join(content_parts)
        
        return {
            "etf_code": etf_detail.get("code", ""),
            "etf_name": etf_detail.get("name", ""),
            "content": content,
            "source": "naver_finance",
            "etf_type": "domestic",
            "category": info.get("분류", ""),
            "metadata": {
                "price": etf_detail.get("price"),
                "nav": nav_value,  # 개선된 NAV 값 사용
                "description": etf_detail.get("description", ""),
                **info
            }
        }


# Example usage
if __name__ == "__main__":
    logger.info("Testing Naver ETF Crawler...")
    
    crawler = NaverETFCrawler()
    
    # Test: Get ETF list
    etfs = crawler.get_etf_list()
    print(f"\nFound {len(etfs)} ETFs")
    if etfs:
        print(f"First ETF: {etfs[0]}")
    
    # Test: Get detail for one ETF
    if etfs:
        code = etfs[0]["code"]
        detail = crawler.get_etf_detail(code)
        if detail:
            print(f"\nDetail for {detail['name']}:")
            print(f"Description: {detail['description'][:100]}...")
            
            # Format for vector DB
            formatted = crawler.format_for_vector_db(detail)
            print(f"\nFormatted content preview:")
            print(formatted['content'][:200] + "...")

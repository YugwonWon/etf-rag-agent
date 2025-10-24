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
        self.etf_list_url = f"{self.base_url}/sise/etf.naver"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        logger.info("Naver ETF Crawler initialized")
    
    def get_etf_list(self) -> List[Dict[str, str]]:
        """
        Get list of all domestic ETFs
        
        Returns:
            List of ETF info dicts with code, name, etc.
        """
        try:
            logger.info("Fetching ETF list from Naver Finance...")
            
            response = requests.get(self.etf_list_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find ETF table
            table = soup.find("table", class_="type_1")
            if not table:
                logger.error("ETF table not found")
                return []
            
            etfs = []
            rows = table.find("tbody").find_all("tr")
            
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 7:
                    continue
                
                # Extract ETF info
                name_link = cols[1].find("a")
                if not name_link:
                    continue
                
                href = name_link.get("href", "")
                code_match = re.search(r"code=(\d+)", href)
                if not code_match:
                    continue
                
                code = code_match.group(1)
                name = name_link.text.strip()
                
                try:
                    price = cols[2].text.strip().replace(",", "")
                    change = cols[3].text.strip()
                    volume = cols[6].text.strip().replace(",", "")
                    
                    etf_info = {
                        "code": code,
                        "name": name,
                        "price": price,
                        "change": change,
                        "volume": volume,
                        "url": f"{self.base_url}/item/main.naver?code={code}"
                    }
                    
                    etfs.append(etf_info)
                
                except (IndexError, AttributeError) as e:
                    logger.debug(f"Error parsing row: {e}")
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
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract basic info
            summary = soup.find("div", class_="wrap_company")
            name = summary.find("h2").text.strip() if summary and summary.find("h2") else "Unknown"
            
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
        # Create rich text content
        content_parts = [
            f"ETF 이름: {etf_detail.get('name', 'N/A')}",
            f"ETF 코드: {etf_detail.get('code', 'N/A')}",
            f"현재가: {etf_detail.get('price', 'N/A')}원",
            f"NAV: {etf_detail.get('nav', 'N/A')}",
            f"\n설명: {etf_detail.get('description', 'N/A')}",
        ]
        
        # Add info table data
        info = etf_detail.get('info', {})
        if info:
            content_parts.append("\n상세 정보:")
            for key, value in info.items():
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
                "nav": etf_detail.get("nav"),
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

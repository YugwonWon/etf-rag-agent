"""
DART (Data Analysis, Retrieval and Transfer System) API Crawler
Crawls ETF disclosure documents from Korean FSS DART
"""

import requests
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger


class DARTCrawler:
    """Crawler for DART ETF disclosure documents"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize DART API crawler
        
        Args:
            api_key: DART API key (get from https://opendart.fss.or.kr/)
        """
        from app.config import get_settings
        settings = get_settings()
        
        self.api_key = api_key or settings.dart_api_key
        self.base_url = "https://opendart.fss.or.kr/api"
        
        if not self.api_key:
            logger.warning(
                "DART API key not set. Get your key from: "
                "https://opendart.fss.or.kr/"
            )
        
        logger.info("DART Crawler initialized")
    
    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, any]
    ) -> Optional[Dict[str, any]]:
        """
        Make API request to DART
        
        Args:
            endpoint: API endpoint
            params: Query parameters
        
        Returns:
            API response dict or None
        """
        if not self.api_key:
            logger.error("DART API key is required")
            return None
        
        try:
            url = f"{self.base_url}/{endpoint}"
            params["crtfc_key"] = self.api_key
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") != "000":
                logger.error(f"DART API error: {data.get('message', 'Unknown error')}")
                return None
            
            return data
        
        except Exception as e:
            logger.error(f"Error making DART request: {e}")
            return None
    
    def search_etf_disclosures(
        self,
        corp_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict[str, any]]:
        """
        Search for ETF-related disclosure documents
        
        Args:
            corp_code: Corporation code (optional)
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            max_results: Maximum number of results
        
        Returns:
            List of disclosure documents
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        
        if not start_date:
            # Default: last 30 days
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        
        params = {
            "bgn_de": start_date,
            "end_de": end_date,
            "page_no": 1,
            "page_count": min(max_results, 100)
        }
        
        if corp_code:
            params["corp_code"] = corp_code
        
        logger.info(f"Searching DART disclosures from {start_date} to {end_date}")
        
        data = self._make_request("list.json", params)
        
        if not data or "list" not in data:
            return []
        
        disclosures = data["list"]
        
        # Filter ETF-related disclosures
        etf_disclosures = [
            d for d in disclosures
            if "ETF" in d.get("report_nm", "").upper() or
               "상장지수" in d.get("report_nm", "")
        ]
        
        logger.info(f"Found {len(etf_disclosures)} ETF-related disclosures")
        return etf_disclosures
    
    def get_company_info(self, corp_code: str) -> Optional[Dict[str, any]]:
        """
        Get company information
        
        Args:
            corp_code: Corporation code
        
        Returns:
            Company info dict
        """
        params = {"corp_code": corp_code}
        
        data = self._make_request("company.json", params)
        
        if data:
            logger.debug(f"Fetched company info for {corp_code}")
        
        return data
    
    def get_document_content(
        self,
        rcept_no: str
    ) -> Optional[str]:
        """
        Get document content (text extraction)
        
        Args:
            rcept_no: Receipt number
        
        Returns:
            Document text content
        """
        try:
            # Note: DART API provides document URL, not direct text
            # For full implementation, you would:
            # 1. Get document URL
            # 2. Download PDF/HTML
            # 3. Extract text
            
            url = f"http://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
            
            logger.info(f"Document URL: {url}")
            
            # Placeholder: In real implementation, download and extract text
            return f"Document link: {url}"
        
        except Exception as e:
            logger.error(f"Error getting document content: {e}")
            return None
    
    def get_etf_prospectus_list(
        self,
        days_back: int = 90
    ) -> List[Dict[str, any]]:
        """
        Get list of ETF prospectus documents
        
        Args:
            days_back: Number of days to look back
        
        Returns:
            List of prospectus documents
        """
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
        
        disclosures = self.search_etf_disclosures(
            start_date=start_date,
            end_date=end_date
        )
        
        # Filter for prospectus-like documents
        prospectus_keywords = ["투자설명서", "간이투자설명서", "교부", "운용"]
        
        prospectus_list = [
            d for d in disclosures
            if any(kw in d.get("report_nm", "") for kw in prospectus_keywords)
        ]
        
        logger.info(f"Found {len(prospectus_list)} ETF prospectus documents")
        return prospectus_list
    
    def format_for_vector_db(
        self,
        disclosure: Dict[str, any],
        content: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Format disclosure for vector database
        
        Args:
            disclosure: Disclosure metadata
            content: Document content (if available)
        
        Returns:
            Formatted dict for vector DB
        """
        corp_name = disclosure.get("corp_name", "")
        report_name = disclosure.get("report_nm", "")
        rcept_no = disclosure.get("rcept_no", "")
        flr_nm = disclosure.get("flr_nm", "")
        rcept_dt = disclosure.get("rcept_dt", "")
        
        # Create content
        if content:
            content_text = content
        else:
            # Create summary from metadata
            content_text = f"""공시 정보
            
회사명: {corp_name}
보고서명: {report_name}
공시제출인: {flr_nm}
접수일자: {rcept_dt}
접수번호: {rcept_no}

문서 링크: http://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}
"""
        
        return {
            "etf_code": rcept_no,  # Use receipt number as unique ID
            "etf_name": corp_name,
            "content": content_text,
            "source": "dart",
            "etf_type": "domestic",
            "category": "공시문서",
            "metadata": {
                "corp_name": corp_name,
                "report_name": report_name,
                "rcept_no": rcept_no,
                "rcept_dt": rcept_dt,
                "flr_nm": flr_nm,
                "corp_code": disclosure.get("corp_code", ""),
            }
        }


# Example usage
if __name__ == "__main__":
    logger.info("Testing DART Crawler...")
    
    # Note: You need a valid DART API key
    crawler = DARTCrawler()
    
    if crawler.api_key:
        # Test: Search ETF disclosures
        disclosures = crawler.search_etf_disclosures(days_back=30)
        
        print(f"\nFound {len(disclosures)} ETF disclosures")
        
        if disclosures:
            print("\nSample disclosure:")
            sample = disclosures[0]
            print(f"  Company: {sample.get('corp_name')}")
            print(f"  Report: {sample.get('report_nm')}")
            print(f"  Date: {sample.get('rcept_dt')}")
            
            # Format for vector DB
            formatted = crawler.format_for_vector_db(sample)
            print(f"\n  Formatted content:")
            print(formatted['content'][:200] + "...")
        
        # Test: Get prospectus list
        prospectuses = crawler.get_etf_prospectus_list(days_back=90)
        print(f"\nFound {len(prospectuses)} prospectus documents")
    
    else:
        print("\nDART API key not configured")
        print("Get your key from: https://opendart.fss.or.kr/")

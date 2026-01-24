"""
Lens.org API Wrapper for Project Aether.
Implements the LensConnector class for patent search operations.
Follows the implementation plan from Section 10.1.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

import httpx
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
)

from project_aether.core.config import get_config

# Configure Logging
logger = logging.getLogger("LensConnector")


class LensAPIError(Exception):
    """Custom exception for Lens.org API failures."""
    pass


class RateLimitError(Exception):
    """Raised when API rate limit is hit."""
    pass


class LensConnector:
    """
    The Researcher Agent's primary tool for accessing Lens.org.
    Implements rate limiting and resilient query execution.
    
    Based on implementation plan Section 10.1.
    """
    
    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize the Lens connector.
        
        Args:
            api_token: Lens.org API token. If None, loads from config.
        """
        self.config = get_config()
        self.api_token = api_token or self.config.lens_org_api_token
        self.base_url = self.config.lens_api_url
        
        if not self.api_token or self.api_token == "your_lens_api_token_here":
            logger.warning("⚠️ No valid LENS_ORG_API_TOKEN configured. API calls will fail.")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        
        # Rate limiting state
        self._requests_made = 0
        self._window_start = datetime.now()
    
    async def _check_rate_limit(self):
        """
        Internal rate limiting to respect API quotas.
        Implements a sliding window approach.
        """
        now = datetime.now()
        window_duration = timedelta(minutes=1)
        
        # Reset counter if window has passed
        if now - self._window_start > window_duration:
            self._requests_made = 0
            self._window_start = now
        
        # Check if we've exceeded the limit
        if self._requests_made >= self.config.max_requests_per_minute:
            sleep_time = 60 - (now - self._window_start).total_seconds()
            if sleep_time > 0:
                logger.info(f"Rate limit reached. Sleeping for {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)
                self._requests_made = 0
                self._window_start = datetime.now()
        
        self._requests_made += 1
    
    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(RateLimitError),
    )
    async def search_patents(self, query_payload: Dict) -> Dict:
        """
        Execute a patent search with exponential backoff for rate limits.
        
        Args:
            query_payload: JSON query payload for Lens.org API
            
        Returns:
            JSON response from Lens.org API
            
        Raises:
            LensAPIError: If the API request fails
            RateLimitError: If rate limit is exceeded (triggers retry)
        """
        await self._check_rate_limit()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.debug(f"Sending query to Lens.org: {query_payload}")
                
                response = await client.post(
                    self.base_url,
                    headers=self.headers,
                    json=query_payload,
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    logger.warning("Rate limit hit (429). Retrying...")
                    raise RateLimitError("API rate limit exceeded")
                
                # Handle other errors
                if response.status_code != 200:
                    error_msg = f"Lens API error {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise LensAPIError(error_msg)
                
                result = response.json()
                total_results = result.get("total", 0)
                logger.info(f"✅ Retrieved {total_results} results from Lens.org")
                
                return result
                
        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {e}")
            raise LensAPIError(f"Request timeout: {e}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise LensAPIError(f"Request error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise LensAPIError(f"Unexpected error: {e}")
    
    def build_anomalous_spark_query(
        self,
        jurisdictions: List[str],
        start_date: str,
        end_date: Optional[str] = None,
    ) -> Dict:
        """
        Construct the complex Boolean query for 'Sparks in Hydrogen'.
        Implements the search strategy from the implementation plan.
        
        Args:
            jurisdictions: List of jurisdiction codes (e.g., ["RU", "PL"])
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format. If None, uses today.
            
        Returns:
            JSON query payload for Lens.org API
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Build the query following the implementation plan structure
        query = {
            "query": {
                "bool": {
                    "must": [
                        # Must contain hydrogen-related terms
                        {
                            "bool": {
                                "should": [
                                    {"match_phrase": {"abstract": "hydrogen"}},
                                    {"match_phrase": {"abstract": "deuterium"}},
                                    {"match_phrase": {"abstract": "protium"}},
                                ]
                            }
                        },
                        # Must be in target jurisdictions
                        {
                            "terms": {
                                "jurisdiction": jurisdictions
                            }
                        },
                        # Must be discontinued/withdrawn in date range
                        {
                            "bool": {
                                "should": [
                                    {"term": {"legal_status.patent_status": "DISCONTINUED"}},
                                    {"term": {"legal_status.patent_status": "WITHDRAWN"}},
                                    {"term": {"legal_status.patent_status": "REJECTED"}},
                                ]
                            }
                        },
                        # Date range filter
                        {
                            "range": {
                                "legal_status.discontinued_date": {
                                    "gte": start_date,
                                    "lte": end_date,
                                }
                            }
                        },
                    ],
                    "should": [
                        # High priority: anomalous terminology
                        {"match_phrase": {"abstract": "anomalous heat"}},
                        {"match_phrase": {"abstract": "excess energy"}},
                        {"match_phrase": {"abstract": "plasma"}},
                        {"match_phrase": {"abstract": "spark"}},
                        {"match_phrase": {"abstract": "discharge"}},
                        {"match_phrase": {"abstract": "cold fusion"}},
                        {"match_phrase": {"abstract": "LENR"}},
                        {"match_phrase": {"abstract": "transmutation"}},
                        # Russian terminology
                        {"match_phrase": {"abstract": "аномальное тепловыделение"}},
                        {"match_phrase": {"abstract": "плазменный вихрь"}},
                        {"match_phrase": {"abstract": "холодный синтез"}},
                    ],
                    "must_not": [
                        # Negative filter for automotive noise
                        {"match_phrase": {"title": "spark plug"}},
                        {"match_phrase": {"abstract": "internal combustion"}},
                        {"match_phrase": {"abstract": "ignition system"}},
                        {"match_phrase": {"title": "ignition coil"}},
                    ],
                    "minimum_should_match": 1,
                }
            },
            "size": 50,  # Retrieve 50 candidates for analysis
            "include": [
                "lens_id",
                "jurisdiction",
                "doc_number",
                "title",
                "abstract",
                "claims",
                "legal_status",
                "applicants",
                "inventors",
                "date_published",
                "classifications_ipcr",
                "classifications_cpc",
            ],
        }
        
        return query
    
    async def search_by_jurisdiction(
        self,
        jurisdiction: str,
        start_date: str,
        end_date: Optional[str] = None,
    ) -> Dict:
        """
        Convenience method to search a single jurisdiction.
        
        Args:
            jurisdiction: Single jurisdiction code (e.g., "RU")
            start_date: Start date in ISO format
            end_date: End date in ISO format
            
        Returns:
            Search results from Lens.org
        """
        query = self.build_anomalous_spark_query([jurisdiction], start_date, end_date)
        return await self.search_patents(query)
    
    async def get_patent_by_lens_id(self, lens_id: str) -> Optional[Dict]:
        """
        Retrieve a specific patent by its Lens ID.
        
        Args:
            lens_id: Lens unique identifier
            
        Returns:
            Patent data or None if not found
        """
        query = {
            "query": {"term": {"lens_id": lens_id}},
            "size": 1,
            "include": [
                "lens_id",
                "jurisdiction",
                "doc_number",
                "title",
                "abstract",
                "claims",
                "legal_status",
                "applicants",
                "inventors",
                "date_published",
                "classifications_ipcr",
                "classifications_cpc",
                "biblio",
            ],
        }
        
        try:
            result = await self.search_patents(query)
            data = result.get("data", [])
            return data[0] if data else None
        except LensAPIError as e:
            logger.error(f"Failed to retrieve patent {lens_id}: {e}")
            return None


# Convenience function for simple usage
async def search_anomalous_patents(
    jurisdictions: List[str],
    days_back: int = 7,
) -> Dict:
    """
    Quick search function for the last N days of anomalous patents.
    
    Args:
        jurisdictions: List of jurisdiction codes
        days_back: Number of days to search back
        
    Returns:
        Search results from Lens.org
    """
    connector = LensConnector()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    query = connector.build_anomalous_spark_query(
        jurisdictions=jurisdictions,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
    )
    
    return await connector.search_patents(query)

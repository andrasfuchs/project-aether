"""
Lens.org API Wrapper for Project Aether.
Implements the LensConnector class for patent search operations.
Follows the implementation plan from Section 10.1.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
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

# Mapping of jurisdiction codes to full country names for logging
JURISDICTION_NAMES = {
    "EP": "European Patent Office",
    "CN": "China",
    "JP": "Japan",
    "US": "United States",
    "DE": "Germany",
    "KR": "Republic of Korea",
    "GB": "United Kingdom",
    "FR": "France",
    "CA": "Canada",
    "RU": "Russia",
    "PL": "Poland",
    "RO": "Romania",
    "CZ": "Czech Republic",
    "NL": "Netherlands",
    "ES": "Spain",
    "IT": "Italy",
    "SE": "Sweden",
    "NO": "Norway",
    "FI": "Finland",
    "HU": "Hungary"
}


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

    @staticmethod
    def _normalize_lens_patent_record(patent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a Lens patent record to the provider-neutral identifier contract.

        The normalized record keeps backwards-compatible Lens fields while adding:
        - `record_id`: canonical application-wide identifier
        - `epo_id`: nullable EPO identifier (always `None` in Lens provider)
        - provider metadata for provider-aware rendering and linking

        Args:
            patent: Raw patent record returned by Lens.org.

        Returns:
            Normalized patent record dictionary.
        """
        normalized = dict(patent)
        lens_id = normalized.get("lens_id")
        normalized["record_id"] = lens_id or normalized.get("record_id") or "UNKNOWN"
        normalized["lens_id"] = lens_id
        normalized.setdefault("epo_id", None)
        normalized["provider_name"] = "lens"
        normalized["provider_record_id"] = normalized["record_id"]
        normalized["provider_record_url"] = (
            f"https://www.lens.org/lens/patent/{lens_id}/frontpage"
            if lens_id
            else None
        )
        normalized.setdefault("provider_api_url", "https://api.lens.org/patent/search")
        return normalized
    
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
                import json
                logger.debug(f"Sending query to Lens.org:\n{json.dumps(query_payload, indent=2)}")
                
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
    
    def build_keyword_search_query(
        self,
        jurisdictions: Optional[List[str]],
        start_date: Optional[str],
        end_date: Optional[str] = None,
        positive_keywords: Optional[List[str]] = None,
        negative_keywords: Optional[List[str]] = None,
        patent_status_filter: Optional[List[str]] = None,
        language: str = "EN",
        limit: Optional[int] = 100,
    ) -> Dict:
        """
        Construct a flexible keyword-based patent search query.
        
        Uses OR logic for positive keywords (match ANY positive keyword).
        Uses AND logic for negative keywords (exclude results containing ANY negative keyword).
        
        Args:
            jurisdictions: List of jurisdiction codes (e.g., ["RU", "PL"]), or None for no jurisdiction filter
            start_date: Start date in ISO format (YYYY-MM-DD), or None for infinite lookback
            end_date: End date in ISO format. If None, uses today.
            positive_keywords: Keywords to include (OR logic)
            negative_keywords: Keywords to exclude (AND exclusion logic)
            patent_status_filter: Optional patent status filter
            language: Language code for the search query (e.g., "EN", "ZH", "AR"). Defaults to "EN".
            limit: Maximum number of results to return (default: 100)
            positive_keywords: Keywords to search for (OR logic - any match returns result)
            negative_keywords: Keywords to exclude (AND logic - exclude if ANY match)
            patent_status_filter: Optional list of patent statuses to filter by (e.g., ["DISCONTINUED", "WITHDRAWN"])
            
        Returns:
            JSON query payload for Lens.org API
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        if positive_keywords is None:
            positive_keywords = []
        if negative_keywords is None:
            negative_keywords = []

        # Clean up empty strings
        positive_keywords = [term for term in positive_keywords if term]
        negative_keywords = [term for term in negative_keywords if term]
        if not positive_keywords:
            raise LensAPIError(
                "Lens keyword search requires at least one include keyword from the active sidebar keyword set."
            )

        must_clauses = []
        
        # Add jurisdiction filter only if jurisdictions are specified
        if jurisdictions is not None and len(jurisdictions) > 0:
            must_clauses.append({
                "terms": {
                    "jurisdiction": jurisdictions
                }
            })
        
        # Add date range filter only if start_date is provided (not infinite)
        if start_date is not None:
            must_clauses.append({
                "range": {
                    "date_published": {
                        "gte": start_date,
                        "lte": end_date,
                    }
                }
            })
        
        # Add patent status filter if provided
        if patent_status_filter is not None and len(patent_status_filter) > 0:
            must_clauses.append({
                "bool": {
                    "should": [
                        {"term": {"legal_status.patent_status": status}}
                        for status in patent_status_filter
                    ]
                }
            })
        
        # Build positive keyword clauses (OR logic - match ANY)
        # Search in abstract, title, and claims for better coverage
        should_clauses = []
        for term in positive_keywords:
            should_clauses.append({
                "bool": {
                    "should": [
                        {"match_phrase": {"abstract": term}},
                        {"match_phrase": {"biblio.invention_title.text": term}},
                        {"match_phrase": {"claim": term}}
                    ]
                }
            })

        # Build negative keyword clauses (AND logic - exclude if ANY match)
        # Check abstract, title, and claims
        must_not_clauses = []
        for term in negative_keywords:
            must_not_clauses.append({
                "bool": {
                    "should": [
                        {"match_phrase": {"abstract": term}},
                        {"match_phrase": {"biblio.invention_title.text": term}},
                        {"match_phrase": {"claim": term}}
                    ]
                }
            })

        # Build the query with OR for positive, AND exclusion for negative
        query = {
            "query": {
                "bool": {
                    "must": must_clauses,
                    "should": should_clauses,
                    "must_not": must_not_clauses,
                    "minimum_should_match": 1 if should_clauses else 0,
                }
            },
            "language": language,
            "include": [
                "lens_id",
                "jurisdiction",
                "doc_number",
                "biblio.invention_title",
                "abstract",
                "claims",
                "legal_status",
                "biblio.parties.applicants",
                "biblio.parties.inventors",
                "date_published",
                "biblio.classifications_ipcr",
                "biblio.classifications_cpc",
            ],
        }

        if limit is not None:
            query["size"] = limit
        
        return query
    
    async def search_by_jurisdiction(
        self,
        jurisdiction: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str] = None,
        positive_keywords: Optional[List[str]] = None,
        negative_keywords: Optional[List[str]] = None,
        patent_status_filter: Optional[List[str]] = None,
        language: str = "EN",
        limit: Optional[int] = 100,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict:
        """
        Convenience method to search with specified language and no jurisdiction filter.
        
        Args:
            jurisdiction: Single jurisdiction code (e.g., "RU"), or None for no filter (used for logging)
            start_date: Start date in ISO format, or None for infinite lookback
            end_date: End date in ISO format
            positive_keywords: Keywords to search for (OR logic)
            negative_keywords: Keywords to exclude (AND logic)
            patent_status_filter: Optional patent status filter
            language: Language code for the search query (e.g., "EN", "ZH", "AR")
            limit: Maximum number of results to return per search (default: 100)
            progress_callback: Optional progress callback for provider-interface
                compatibility; not used by Lens connector.
            
        Returns:
            Search results from Lens.org with metadata about filtering
        """
        jurisdictions = [jurisdiction] if jurisdiction else None
        _ = progress_callback
        
        # Build the query with language parameter

        query = self.build_keyword_search_query(
            jurisdictions,
            start_date,
            end_date,
            positive_keywords=positive_keywords,
            negative_keywords=negative_keywords,
            patent_status_filter=patent_status_filter,
            language=language,
            limit=limit,
        )
        
        # Execute the search
        result = await self.search_patents(query)
        
        # Extract results for additional filtering and logging
        raw_results = result.get("data", [])
        total_from_api = result.get("total", 0)
        
        # The API already filters by negative keywords in the query,
        # but we'll do a secondary check and count for logging accuracy
        filtered_results = []
        excluded_count = 0
        
        for patent in raw_results:
            # Check if any negative keyword appears in abstract or title
            abstract_text = ""
            if "abstract" in patent:
                if isinstance(patent["abstract"], list):
                    abstract_text = " ".join([a.get("text", "") for a in patent["abstract"]]).lower()
                elif isinstance(patent["abstract"], str):
                    abstract_text = patent["abstract"].lower()
            
            title_text = ""
            if "biblio" in patent and "invention_title" in patent["biblio"]:
                title_data = patent["biblio"]["invention_title"]
                if isinstance(title_data, list):
                    title_text = " ".join([t.get("text", "") for t in title_data]).lower()
                elif isinstance(title_data, dict):
                    title_text = title_data.get("text", "").lower()
                elif isinstance(title_data, str):
                    title_text = title_data.lower()
            
            combined_text = abstract_text + " " + title_text
            
            # Check for negative keywords
            has_negative = False
            if negative_keywords:
                for neg_term in negative_keywords:
                    if neg_term.lower() in combined_text:
                        has_negative = True
                        excluded_count += 1
                        break
            
            if not has_negative:
                filtered_results.append(patent)
        
        # Update result with filtered and normalized data
        result["data"] = [
            self._normalize_lens_patent_record(patent)
            for patent in filtered_results
        ]
        result["filtered_total"] = len(filtered_results)
        
        # Generate detailed logging
        if jurisdiction:
            country_name = JURISDICTION_NAMES.get(jurisdiction, jurisdiction)
        else:
            country_name = "All Countries"
        
        # Format keywords for logging (truncate if too long)
        pos_keywords_str = ", ".join([f"'{kw}'" for kw in (positive_keywords or [])[:3]])
        if positive_keywords and len(positive_keywords) > 3:
            pos_keywords_str += f" (+{len(positive_keywords) - 3} more)"
        
        neg_keywords_str = ", ".join([f"'{kw}'" for kw in (negative_keywords or [])[:3]])
        if negative_keywords and len(negative_keywords) > 3:
            neg_keywords_str += f" (+{len(negative_keywords) - 3} more)"
        
        # Create the detailed log message
        logger.info(
            f"✅ Completed patent search in {country_name} "
            f"with {language} keywords: "
            f"positive={pos_keywords_str or 'none'} and "
            f"negative={neg_keywords_str or 'none'} "
            f"with {len(filtered_results)} results "
            f"(from {total_from_api} API results, {excluded_count} filtered by negative keywords)"
        )
        
        return result
    
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
                "biblio.invention_title",
                "abstract",
                "claims",
                "legal_status",
                "biblio.parties.applicants",
                "biblio.parties.inventors",
                "date_published",
                "biblio.classifications_ipcr",
                "biblio.classifications_cpc",
                "biblio",
            ],
        }
        
        try:
            result = await self.search_patents(query)
            data = result.get("data", [])
            if not data:
                return None
            return self._normalize_lens_patent_record(data[0])
        except LensAPIError as e:
            logger.error(f"Failed to retrieve patent {lens_id}: {e}")
            return None

    async def get_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Provider-neutral identifier lookup helper.

        Args:
            identifier: Lens identifier value.

        Returns:
            Patent record dictionary or `None`.
        """
        return await self.get_patent_by_lens_id(identifier)

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a lightweight Lens provider health check.

        This check validates token presence and token formatting readiness.
        It intentionally avoids a live search request to prevent unnecessary
        quota consumption in routine diagnostics.

        Returns:
            Dictionary containing health status details.
        """
        if not self.api_token or self.api_token == "your_lens_api_token_here":
            return {
                "provider": "lens",
                "ok": False,
                "message": "Missing or placeholder Lens API token.",
            }

        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return {
                "provider": "lens",
                "ok": False,
                "message": "Lens authorization header is not configured correctly.",
            }

        return {
            "provider": "lens",
            "ok": True,
            "message": "Lens token is configured (connectivity not probed).",
        }


# Convenience function for simple usage
async def search_patents_by_keywords(
    jurisdictions: List[str],
    positive_keywords: List[str],
    negative_keywords: Optional[List[str]] = None,
    days_back: int = 7,
    patent_status_filter: Optional[List[str]] = None,
) -> Dict:
    """
    Quick search function for the last N days using keyword filtering.
    
    Args:
        jurisdictions: List of jurisdiction codes
        positive_keywords: Keywords to search for (OR logic)
        negative_keywords: Keywords to exclude (AND logic)
        days_back: Number of days to search back
        patent_status_filter: Optional patent status filter
        
    Returns:
        Search results from Lens.org
    """
    connector = LensConnector()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    query = connector.build_keyword_search_query(
        jurisdictions=jurisdictions,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        positive_keywords=positive_keywords,
        negative_keywords=negative_keywords,
        patent_status_filter=patent_status_filter,
    )
    
    return await connector.search_patents(query)

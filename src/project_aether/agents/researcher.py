import os
import logging
import httpx
import asyncio
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from typing import Dict, List, Any

# Configure Logging
logger = logging.getLogger("ResearcherAgent")

class LensAPIError(Exception):
    """Custom exception for API failures."""
    pass

# --- 1. The Tool Definition (The "Hard Skills") ---

class LensResearcher:
    """
    Handles the raw HTTP interaction with Lens.org.
    """
    def __init__(self):
        self.api_token = os.getenv("LENS_ORG_API_TOKEN")
        self.base_url = "https://api.lens.org/patent/search"
        
        if not self.api_token:
            logger.warning("⚠️ No LENS_ORG_API_TOKEN found in .env. Using Mock Data mode.")

    def _build_query(self, jurisdictions: List[str], date_range: tuple) -> Dict:
        """
        Constructs the strict Boolean query for 'Dead Hydrogen Patents'.
        """
        start_date, end_date = date_range
        
        # 1. Base Query: "Sparks in Hydrogen" context
        # We look for 'hydrogen' AND ('spark' OR 'plasma' OR 'heat')
        keyword_block = {
            "bool": {
                "must": [
                    {"match": {"abstract": "hydrogen"}}, 
                    {"bool": {
                        "should": [
                            {"match": {"abstract": "plasma"}},
                            {"match": {"abstract": "spark"}},
                            {"match": {"abstract": "anomalous heat"}},
                            {"match": {"abstract": "excess energy"}}
                        ]
                    }}
                ]
            }
        }

        # 2. Filter: Only Rejected/Withdrawn (The "Negative Space")
        # specific codes for Russia (FC9A) vs General Withdrawn
        status_filter = {
            "bool": {
                "should": [
                    {"term": {"legal_status.patent_status": "DISCONTINUED"}},
                    {"term": {"legal_status.patent_status": "WITHDRAWN"}},
                    {"term": {"legal_status.patent_status": "REJECTED"}},
                    # Explicit check for Russian refusal code if possible in free tier keywords
                    {"term": {"legal_status.events.event_code": "FC9A"}} 
                ]
            }
        }

        # 3. Filter: Jurisdiction
        jurisdiction_filter = {"terms": {"jurisdiction": jurisdictions}}

        # Assemble Payload
        return {
            "query": {
                "bool": {
                    "must": [keyword_block, status_filter, jurisdiction_filter]
                }
            },
            "size": 50,  # Batch size
            "include": ["lens_id", "jurisdiction", "doc_number", "date_published", "biblio.invention_title", "abstract", "legal_status"]
        }

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3)
    )
    async def fetch_patents(self, jurisdictions: List[str], date_range: tuple) -> List[Dict]:
        """
        Executes search with retries. Returns raw JSON list.
        """
        # MOCK MODE (If no key provided)
        if not self.api_token:
            await asyncio.sleep(1) # Simulate network lag
            return [
                {
                    "lens_id": "000-MOCK-RU", 
                    "jurisdiction": "RU", 
                    "doc_number": "RU2025123C1",
                    "abstract": [{"text": "Method for generating anomalous plasma vortex in hydrogen medium."}], 
                    "legal_status": {"patent_status": "REJECTED", "events": [{"event_code": "FC9A"}]}
                }
            ]

        # REAL MODE
        payload = self._build_query(jurisdictions, date_range)
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=headers, timeout=30.0)
            
            if response.status_code == 429:
                logger.warning("Rate limit hit. Tenacity will retry...")
                raise httpx.HTTPStatusError("Rate Limit", request=response.request, response=response)
            
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])

# --- 2. The Node Entry Point (The "LangGraph Wrapper") ---

async def research_jurisdiction(state: Dict) -> Dict:
    """
    The Node function called by the Manager Graph.
    Receives state -> calls Tool -> updates state.
    """
    logger.info("--- 📡 RESEARCHER: Scanning Patent Databases ---")
    
    jurisdictions = state.get("target_jurisdictions", ["RU"])
    date_range = state.get("date_range", ("2024-01-01", "2024-01-07"))
    
    researcher = LensResearcher()
    
    try:
        results = await researcher.fetch_patents(jurisdictions, date_range)
        count = len(results)
        logger.info(f"--- 📡 RESEARCHER: Found {count} candidates ---")
        
        # Return ONLY the key we want to update in the state
        # LangGraph merges this dict into the global state
        return {"raw_patents": results}
        
    except Exception as e:
        logger.error(f"Research failed: {e}")
        return {"error_log": [str(e)]}
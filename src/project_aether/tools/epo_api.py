"""
European Patent Office (EPO OPS) API wrapper for Project Aether.

This module provides the `EPOConnector` class as a drop-in search provider
that normalizes OPS XML responses into the Project Aether patent record shape.

Design goals:
- EPO-first provider behavior with Lens-compatible output keys.
- Dual identifier transition support:
  - `record_id`: canonical identifier used by the application.
  - `epo_id`: nullable DOCDB-style identifier for EPO records.
  - `lens_id`: nullable compatibility field (always `None` for EPO records).
- Best-effort OPS CQL approximation of existing keyword search semantics.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from project_aether.core.config import get_config
from project_aether.core.keywords import DEFAULT_KEYWORDS

logger = logging.getLogger("EPOConnector")

MAX_PRIMARY_TERMS = 8
MAX_FALLBACK_TERMS = 4
MAX_PRIMARY_TOKEN_BUDGET = 18
MAX_FALLBACK_TOKEN_BUDGET = 10


class EPOAPIError(Exception):
    """Raised when an EPO OPS API call fails or returns invalid data."""


class EPORateLimitError(Exception):
    """Raised when EPO OPS rate limiting is encountered."""


class EPOConnector:
    """
    Connector for the EPO Open Patent Services (OPS) API.

    Public methods mirror existing connector usage so service-layer integration
    can switch providers with minimal orchestration changes.
    """

    def __init__(
        self,
        consumer_key: Optional[str] = None,
        consumer_secret: Optional[str] = None,
    ) -> None:
        """
        Initialize the EPO connector.

        Args:
            consumer_key: EPO OPS consumer key. If omitted, loaded from config.
            consumer_secret: EPO OPS consumer secret. If omitted, loaded from config.
        """
        self.config = get_config()
        self.consumer_key = consumer_key or self.config.epo_consumer_key
        self.consumer_secret = consumer_secret or self.config.epo_consumer_secret
        self.base_url = self.config.epo_ops_base_url.rstrip("/")
        self.auth_url = self.config.epo_ops_auth_url

        if not self.consumer_key or not self.consumer_secret:
            logger.warning(
                "⚠️ No valid EPO OPS credentials configured. API calls will fail."
            )

        self._requests_made = 0
        self._window_start = datetime.now()
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    async def _check_rate_limit(self) -> None:
        """
        Apply simple minute-window throttling before each OPS request.

        This uses project-wide rate-limit configuration values and is designed
        to reduce likelihood of OPS fair-use throttling.
        """
        now = datetime.now()
        window_duration = timedelta(minutes=1)

        if now - self._window_start > window_duration:
            self._requests_made = 0
            self._window_start = now

        if self._requests_made >= self.config.max_requests_per_minute:
            sleep_time = 60 - (now - self._window_start).total_seconds()
            if sleep_time > 0:
                logger.info("EPO rate window reached. Sleeping for %.1fs", sleep_time)
                await asyncio.sleep(sleep_time)
                self._requests_made = 0
                self._window_start = datetime.now()

        self._requests_made += 1

    async def _get_access_token(self, force_refresh: bool = False) -> str:
        """
        Retrieve and cache an OAuth2 access token for OPS.

        Args:
            force_refresh: If True, bypasses cache and requests a fresh token.

        Returns:
            A bearer token string.

        Raises:
            EPOAPIError: If credentials are missing or token request fails.
        """
        if not self.consumer_key or not self.consumer_secret:
            raise EPOAPIError("Missing EPO OPS credentials (consumer key/secret).")

        now = datetime.utcnow()
        if (
            not force_refresh
            and self._access_token
            and self._token_expires_at
            and now < self._token_expires_at
        ):
            return self._access_token

        timeout = float(self.config.epo_request_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self.auth_url,
                data={"grant_type": "client_credentials"},
                auth=(self.consumer_key, self.consumer_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if response.status_code != 200:
            raise EPOAPIError(
                f"EPO auth error {response.status_code}: {response.text}"
            )

        payload = response.json()
        token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 1200))
        if not token:
            raise EPOAPIError("EPO auth response missing access_token.")

        self._access_token = token
        self._token_expires_at = now + timedelta(seconds=max(60, expires_in - 60))
        return token

    @staticmethod
    def _escape_cql_term(term: str) -> str:
        """Sanitize and escape user keyword text for safe CQL embedding."""
        cleaned = re.sub(r"[^0-9A-Za-z\s\-\+/]", " ", term)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned.replace('"', " ")

    @staticmethod
    def _clip_terms(
        terms: List[str],
        max_terms: int,
        max_total_tokens: Optional[int] = None,
    ) -> List[str]:
        """Return a sanitized, bounded list of non-empty keyword terms."""
        output: List[str] = []
        used_tokens = 0
        for term in terms:
            if len(output) >= max_terms:
                break
            if not term:
                continue
            value = EPOConnector._escape_cql_term(term)
            if value:
                token_count = len([part for part in value.split(" ") if part])
                if max_total_tokens is not None and (used_tokens + token_count) > max_total_tokens:
                    continue
                output.append(value)
                used_tokens += token_count
        return output

    def _build_ops_cql(
        self,
        jurisdictions: Optional[List[str]],
        start_date: Optional[str],
        end_date: Optional[str],
        positive_keywords: List[str],
        negative_keywords: List[str],
        *,
        max_positive_terms: int = MAX_PRIMARY_TERMS,
        max_total_tokens: int = MAX_PRIMARY_TOKEN_BUDGET,
        include_negative: bool = False,
        include_date: bool = True,
    ) -> str:
        """
        Build a best-effort OPS CQL query from Aether keyword filters.

        Approximation notes:
        - Positive terms are OR'ed across title/abstract/claims.
        - Negative terms are excluded with NOT clauses.
        - Jurisdiction filtering uses publication number prefix heuristics.
        - Date filtering uses publication date range syntax when provided.

        Args:
            jurisdictions: Optional list of jurisdiction codes.
            start_date: Optional start date in YYYY-MM-DD.
            end_date: Optional end date in YYYY-MM-DD.
            positive_keywords: Include terms.
            negative_keywords: Exclude terms.

        Returns:
            OPS CQL query string.
        """
        clauses: List[str] = []

        positive_terms = self._clip_terms(
            positive_keywords,
            max_positive_terms,
            max_total_tokens=max_total_tokens,
        )
        negative_terms = self._clip_terms(
            negative_keywords,
            max_positive_terms,
            max_total_tokens=max_total_tokens,
        )

        include_clauses: List[str] = []
        for esc in positive_terms:
            include_clauses.append(
                f'(ti all "{esc}" OR ab all "{esc}")'
            )
        if include_clauses:
            clauses.append("(" + " OR ".join(include_clauses) + ")")

        if include_negative and negative_terms:
            exclude_clauses: List[str] = []
            for esc in negative_terms:
                exclude_clauses.append(
                    f'(ti all "{esc}" OR ab all "{esc}")'
                )
            clauses.append("NOT (" + " OR ".join(exclude_clauses) + ")")

        if jurisdictions:
            jurisdiction_filters = [f"pn={j.upper()}*" for j in jurisdictions]
            clauses.append("(" + " OR ".join(jurisdiction_filters) + ")")

        if include_date and start_date:
            start = start_date.replace("-", "")
            end = (end_date or datetime.now().strftime("%Y-%m-%d")).replace("-", "")
            clauses.append(f'pd within "{start} {end}"')

        if not clauses:
            return 'ti all "hydrogen"'

        return " AND ".join(clauses)

    def _build_field_specific_cql(
        self,
        *,
        field: str,
        jurisdictions: Optional[List[str]],
        start_date: Optional[str],
        end_date: Optional[str],
        positive_keywords: List[str],
        max_positive_terms: int = MAX_PRIMARY_TERMS,
        max_total_tokens: int = MAX_PRIMARY_TOKEN_BUDGET,
        include_date: bool = True,
    ) -> str:
        """
        Build a CQL query constrained to a single OPS text field.

        Args:
            field: OPS field token (`ti` for title, `ab` for abstract).
            jurisdictions: Optional list of jurisdiction codes.
            start_date: Optional start date in YYYY-MM-DD.
            end_date: Optional end date in YYYY-MM-DD.
            positive_keywords: Include terms.
            max_positive_terms: Max number of positive terms used.
            max_total_tokens: Max total token budget across terms.
            include_date: Whether to include publication date range clause.

        Returns:
            OPS CQL query string.
        """
        clauses: List[str] = []

        positive_terms = self._clip_terms(
            positive_keywords,
            max_positive_terms,
            max_total_tokens=max_total_tokens,
        )

        include_clauses: List[str] = []
        for esc in positive_terms:
            include_clauses.append(f'{field} all "{esc}"')
        if include_clauses:
            clauses.append("(" + " OR ".join(include_clauses) + ")")

        if jurisdictions:
            jurisdiction_filters = [f"pn={j.upper()}*" for j in jurisdictions]
            clauses.append("(" + " OR ".join(jurisdiction_filters) + ")")

        if include_date and start_date:
            start = start_date.replace("-", "")
            end = (end_date or datetime.now().strftime("%Y-%m-%d")).replace("-", "")
            clauses.append(f'pd within "{start} {end}"')

        if not clauses:
            return 'ti all "hydrogen"'

        return " AND ".join(clauses)

    @staticmethod
    def _merge_records_by_id(
        record_groups: List[List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """Merge and deduplicate patent records by canonical `record_id`."""
        merged: Dict[str, Dict[str, Any]] = {}
        for group in record_groups:
            for record in group:
                record_id = record.get("record_id")
                if record_id and record_id not in merged:
                    merged[record_id] = record
        return list(merged.values())

    @staticmethod
    def _build_relaxed_unfielded_cql(terms: List[str], max_terms: int = 4) -> str:
        """
        Build a relaxed CQL query using unfielded phrase clauses.

        This is used as a diagnostics fallback when fielded queries return
        zero records. It prioritizes recall over precision.
        """
        picked = EPOConnector._clip_terms(terms, max_terms=max_terms)
        if not picked:
            return 'spark'
        if len(picked) == 1:
            return f'"{picked[0]}"'
        return " OR ".join(f'"{item}"' for item in picked)

    @staticmethod
    def _build_relaxed_ta_cql(terms: List[str], max_terms: int = 4) -> str:
        """Build a diagnostics fallback CQL using `ta` field clauses."""
        picked = EPOConnector._clip_terms(terms, max_terms=max_terms)
        if not picked:
            return "ta=spark"
        if len(picked) == 1:
            return f'ta="{picked[0]}"'
        return " OR ".join(f'ta="{item}"' for item in picked)

    @staticmethod
    def _build_relaxed_bare_or_cql(terms: List[str], max_terms: int = 4) -> str:
        """Build a diagnostics fallback CQL using bare terms with OR."""
        picked = EPOConnector._clip_terms(terms, max_terms=max_terms)
        if not picked:
            return "spark"
        if len(picked) == 1:
            return picked[0]
        return " OR ".join(picked)

    @staticmethod
    def _namespace_wild(path: str) -> str:
        """Convert `a/b/c` path to namespace-agnostic ElementTree path."""
        return "/".join(f"{{*}}{node}" for node in path.split("/"))

    @staticmethod
    def _first_text(root: ET.Element, *paths: str) -> Optional[str]:
        """Return the first non-empty text value matching the provided paths."""
        for path in paths:
            node = root.find(EPOConnector._namespace_wild(path))
            if node is not None and node.text and node.text.strip():
                return node.text.strip()
        return None

    def _extract_title(self, root: ET.Element) -> List[Dict[str, str]]:
        """Extract invention titles from OPS XML as Lens-compatible list objects."""
        titles: List[Dict[str, str]] = []
        for node in root.findall(self._namespace_wild("bibliographic-data/invention-title")):
            text = (node.text or "").strip()
            if text:
                titles.append({"lang": node.attrib.get("lang", "en"), "text": text})
        return titles

    def _extract_abstract(self, root: ET.Element) -> List[Dict[str, str]]:
        """Extract abstract paragraph text from OPS XML."""
        abstracts: List[Dict[str, str]] = []
        for abstract in root.findall(self._namespace_wild("abstract")):
            lang = abstract.attrib.get("lang", "unknown")
            parts = []
            for p in abstract.findall(self._namespace_wild("p")):
                if p.text and p.text.strip():
                    parts.append(p.text.strip())
            text = " ".join(parts).strip()
            if text:
                abstracts.append({"lang": lang.lower(), "text": text})
        return abstracts

    def _extract_parties(self, root: ET.Element, party_type: str) -> List[Dict[str, Any]]:
        """Extract applicant or inventor party entries in compatibility shape."""
        parties: List[Dict[str, Any]] = []
        for node in root.findall(
            self._namespace_wild(f"bibliographic-data/parties/{party_type}s/{party_type}")
        ):
            name = self._first_text(node, "applicant-name/name", "inventor-name/name")
            if name:
                parties.append({"extracted_name": {"value": name}})
        return parties

    def _extract_classifications(self, root: ET.Element, tag: str) -> List[Dict[str, str]]:
        """Extract IPC/CPC-style symbols from OPS XML elements."""
        output: List[Dict[str, str]] = []
        for node in root.findall(self._namespace_wild(f"bibliographic-data/{tag}")):
            symbol = "".join(node.itertext()).strip()
            if symbol:
                output.append({"symbol": symbol})
        return output

    def _normalize_exchange_document(
        self,
        doc: ET.Element,
        provider_record_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Normalize an OPS `exchange-document` element into app record format.

        Args:
            doc: XML element representing an exchange document.
            provider_record_url: Optional provider URL associated with the record.

        Returns:
            Normalized patent record dictionary.
        """
        country = doc.attrib.get("country", "UNKNOWN")
        doc_number = doc.attrib.get("doc-number") or self._first_text(
            doc,
            "bibliographic-data/publication-reference/document-id/doc-number",
        ) or "UNKNOWN"
        kind = doc.attrib.get("kind", "")

        epo_id = f"{country}{doc_number}{kind}".strip()
        record_id = epo_id

        title = self._extract_title(doc)
        abstract = self._extract_abstract(doc)

        published_date = self._first_text(
            doc,
            "bibliographic-data/publication-reference/document-id/date",
        )
        if published_date and len(published_date) == 8:
            published_date = (
                f"{published_date[0:4]}-{published_date[4:6]}-{published_date[6:8]}"
            )

        claims = []
        legal_status = {
            "patent_status": "UNKNOWN",
            "events": [],
        }

        return {
            "record_id": record_id,
            "lens_id": None,
            "epo_id": epo_id,
            "provider_name": "epo",
            "provider_record_id": record_id,
            "provider_record_url": provider_record_url,
            "provider_api_url": provider_record_url,
            "jurisdiction": country,
            "doc_number": doc_number,
            "publication_reference": {
                "country": country,
                "doc_number": doc_number,
                "kind": kind,
            },
            "biblio": {
                "invention_title": title,
                "parties": {
                    "applicants": self._extract_parties(doc, "applicant"),
                    "inventors": self._extract_parties(doc, "inventor"),
                },
                "classifications_ipcr": self._extract_classifications(
                    doc, "classifications-ipcr"
                ),
                "classifications_cpc": self._extract_classifications(
                    doc, "patent-classifications"
                ),
            },
            "abstract": abstract,
            "claims": claims,
            "legal_status": legal_status,
            "date_published": published_date,
        }

    def _normalize_entry(self, entry: ET.Element) -> Dict[str, Any]:
        """
        Normalize one OPS `entry` into the app's patent record contract.

        Returns a record with dual-field identifiers, provider metadata, and
        nested `biblio` structures compatible with downstream analysis code.
        """
        doc = entry.find(self._namespace_wild("content/world-patent-data/exchange-documents/exchange-document"))
        if doc is None:
            doc = entry.find(self._namespace_wild("exchange-document"))
        if doc is None:
            doc = entry.find(".//{*}exchange-document")

        if doc is None:
            return {}

        provider_record_url = None
        for link in entry.findall(self._namespace_wild("link")):
            href = link.attrib.get("href")
            if href:
                provider_record_url = href
                break
        return self._normalize_exchange_document(doc, provider_record_url=provider_record_url)

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(EPORateLimitError),
    )
    async def search_patents(self, query_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an OPS search request and normalize returned records.

        Args:
            query_payload: Dictionary containing:
                - `cql`: OPS CQL query string.
                - `limit`: Optional maximum records for the first range page.
                - `offset`: Optional 1-based start index (default 1).

        Returns:
            Dictionary with `data`, `total`, and provider metadata.

        Raises:
            EPOAPIError: On request/parse failures.
            EPORateLimitError: On 429 / fair-use backoff conditions.
        """
        await self._check_rate_limit()
        token = await self._get_access_token()

        cql = query_payload.get("cql", "").strip()
        if not cql:
            raise EPOAPIError("Missing CQL query string for EPO search.")

        limit = int(query_payload.get("limit") or 25)
        offset = int(query_payload.get("offset") or 1)
        range_end = max(offset, offset + max(1, limit) - 1)

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/xml",
            "Range": f"{offset}-{range_end}",
        }

        endpoint_candidates = query_payload.get(
            "endpoint_candidates",
            ["/published-data/search/biblio", "/published-data/search"],
        )
        if isinstance(endpoint_candidates, str):
            endpoint_candidates = [endpoint_candidates]

        timeout = float(self.config.epo_request_timeout_seconds)

        try:
            endpoint_attempts: List[Dict[str, Any]] = []
            best_result: Optional[Dict[str, Any]] = None

            async with httpx.AsyncClient(timeout=timeout) as client:
                for endpoint_used in endpoint_candidates:
                    url = f"{self.base_url}{endpoint_used}"
                    response = await client.get(
                        url,
                        params={"q": cql},
                        headers=headers,
                    )

                    if response.status_code == 401:
                        refreshed = await self._get_access_token(force_refresh=True)
                        headers["Authorization"] = f"Bearer {refreshed}"
                        response = await client.get(
                            url,
                            params={"q": cql},
                            headers=headers,
                        )

                    if response.status_code == 429:
                        raise EPORateLimitError("EPO OPS rate limit exceeded.")
                    if response.status_code >= 500:
                        endpoint_attempts.append(
                            {
                                "endpoint": endpoint_used,
                                "status_code": response.status_code,
                                "error": response.text[:300],
                            }
                        )
                        continue
                    if response.status_code == 404:
                        endpoint_attempts.append(
                            {
                                "endpoint": endpoint_used,
                                "status_code": response.status_code,
                                "error": "Endpoint not found",
                            }
                        )
                        continue
                    if response.status_code != 200:
                        raise EPOAPIError(
                            f"EPO search error {response.status_code}: {response.text}"
                        )

                    root = ET.fromstring(response.text)
                    fault_node = root.find(".//{*}fault")
                    if fault_node is not None:
                        code = root.findtext(".//{*}code") or "UNKNOWN"
                        message = root.findtext(".//{*}message") or "Unknown OPS fault"
                        raise EPOAPIError(f"EPO search fault {code}: {message}")

                    entries = root.findall(".//{*}entry")
                    docs = root.findall(".//{*}exchange-document")

                    total_available: Optional[int] = None
                    total_node = root.find(".//{*}totalResults")
                    if total_node is not None and total_node.text and total_node.text.strip().isdigit():
                        total_available = int(total_node.text.strip())
                    if total_available is None:
                        biblio_search_node = root.find(".//{*}biblio-search")
                        if biblio_search_node is not None:
                            attr_val = biblio_search_node.attrib.get("total-result-count")
                            if attr_val and str(attr_val).isdigit():
                                total_available = int(str(attr_val))
                    if total_available is None:
                        range_node = root.find(".//{*}range")
                        if range_node is not None:
                            for attr_name in ("total-result-count", "totalResultCount", "total"):
                                attr_val = range_node.attrib.get(attr_name)
                                if attr_val and str(attr_val).isdigit():
                                    total_available = int(str(attr_val))
                                    break
                    if total_available is None:
                        for attr_name in ("total-result-count", "totalResultCount", "total"):
                            attr_val = root.attrib.get(attr_name)
                            if attr_val and str(attr_val).isdigit():
                                total_available = int(str(attr_val))
                                break

                    records = [self._normalize_entry(entry) for entry in entries]
                    records = [r for r in records if r]

                    if not records and docs:
                        records = [self._normalize_exchange_document(doc) for doc in docs]
                        records = [r for r in records if r]

                    endpoint_attempts.append(
                        {
                            "endpoint": endpoint_used,
                            "status_code": response.status_code,
                            "raw_entry_count": len(entries),
                            "raw_document_count": len(docs),
                            "normalized_count": len(records),
                            "total_available": total_available,
                            "root_tag": root.tag,
                        }
                    )

                    current_result = {
                        "data": records,
                        "total": len(records),
                        "total_available": total_available,
                        "raw_entry_count": len(entries),
                        "raw_document_count": len(docs),
                        "normalized_count": len(records),
                        "endpoint_used": endpoint_used,
                        "endpoint_attempts": endpoint_attempts,
                        "cql_used": cql,
                        "response_excerpt": response.text[:800],
                        "provider": "epo",
                        "query": cql,
                    }

                    if best_result is None:
                        best_result = current_result

                    if len(records) > 0 or (total_available is not None and total_available > 0):
                        return current_result

            if best_result is not None:
                best_result["endpoint_attempts"] = endpoint_attempts
                return best_result

            raise EPOAPIError("EPO search failed: no valid endpoint response received.")
        except ET.ParseError as exc:
            raise EPOAPIError(f"Failed to parse EPO XML response: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise EPOAPIError(f"EPO request timeout: {exc}") from exc
        except httpx.RequestError as exc:
            raise EPOAPIError(f"EPO request error: {exc}") from exc

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
    ) -> Dict[str, Any]:
        """
        Build a provider query payload for OPS search.

        Notes:
            `patent_status_filter` and `language` are currently accepted for API
            compatibility with the existing search flow but are only partially
            representable in OPS CQL search.

        Args:
            jurisdictions: Optional jurisdiction list.
            start_date: Optional start date (YYYY-MM-DD).
            end_date: Optional end date (YYYY-MM-DD).
            positive_keywords: Include terms.
            negative_keywords: Exclude terms.
            patent_status_filter: Reserved for future legal endpoint integration.
            language: Reserved for compatibility.
            limit: Maximum records requested from OPS.

        Returns:
            Query payload dictionary for `search_patents`.
        """
        _ = patent_status_filter
        _ = language

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        if positive_keywords is None:
            positive_keywords = DEFAULT_KEYWORDS.get("English", {}).get("positive", [])
        if negative_keywords is None:
            negative_keywords = DEFAULT_KEYWORDS.get("English", {}).get("negative", [])

        positive_keywords = [term for term in positive_keywords if term]
        negative_keywords = [term for term in negative_keywords if term]

        cql = self._build_ops_cql(
            jurisdictions=jurisdictions,
            start_date=start_date,
            end_date=end_date,
            positive_keywords=positive_keywords,
            negative_keywords=negative_keywords,
            include_negative=False,
        )
        logger.debug("EPO primary CQL: %s", cql)

        payload: Dict[str, Any] = {
            "cql": cql,
            "limit": limit or 100,
            "offset": 1,
        }
        return payload

    @staticmethod
    def _contains_any_term(text: str, terms: Optional[List[str]]) -> bool:
        """Return True if any term is present in text, case-insensitive."""
        if not text or not terms:
            return False
        lowered = text.lower()
        return any(term.lower() in lowered for term in terms if term)

    def _apply_negative_keyword_filter(
        self,
        patents: List[Dict[str, Any]],
        negative_keywords: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """
        Apply secondary negative-keyword filtering on normalized records.

        This preserves behavior similar to the existing Lens connector by adding
        a client-side safeguard where provider query semantics differ.
        """
        if not negative_keywords:
            return patents

        filtered: List[Dict[str, Any]] = []
        for patent in patents:
            title_items = patent.get("biblio", {}).get("invention_title", [])
            title_text = " ".join(
                item.get("text", "")
                for item in title_items
                if isinstance(item, dict)
            )

            abstract_items = patent.get("abstract", [])
            abstract_text = " ".join(
                item.get("text", "")
                for item in abstract_items
                if isinstance(item, dict)
            )

            claims = patent.get("claims")
            claims_text = ""
            if isinstance(claims, str):
                claims_text = claims
            elif isinstance(claims, list):
                claims_text = " ".join(
                    item.get("text", "")
                    for item in claims
                    if isinstance(item, dict)
                )

            combined = f"{title_text} {abstract_text} {claims_text}".strip()
            if not self._contains_any_term(combined, negative_keywords):
                filtered.append(patent)

        return filtered

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
    ) -> Dict[str, Any]:
        """
        Search patents using OPS with compatibility-oriented method signature.

        Args:
            jurisdiction: Optional single jurisdiction filter.
            start_date: Optional start date in YYYY-MM-DD.
            end_date: Optional end date in YYYY-MM-DD.
            positive_keywords: Include terms.
            negative_keywords: Exclude terms.
            patent_status_filter: Reserved for future legal endpoint integration.
            language: Reserved for compatibility.
            limit: Max records requested.

        Returns:
            Search results dictionary with normalized records.
        """
        jurisdictions = [jurisdiction] if jurisdiction else None
        query_payload = self.build_keyword_search_query(
            jurisdictions=jurisdictions,
            start_date=start_date,
            end_date=end_date,
            positive_keywords=positive_keywords,
            negative_keywords=negative_keywords,
            patent_status_filter=patent_status_filter,
            language=language,
            limit=limit,
        )
        strategy_attempts: List[Dict[str, Any]] = []
        result: Dict[str, Any] = {}

        field_payloads = [
            (
                "title-only",
                self._build_field_specific_cql(
                    field="ti",
                    jurisdictions=jurisdictions,
                    start_date=start_date,
                    end_date=end_date,
                    positive_keywords=positive_keywords or [],
                    max_positive_terms=MAX_FALLBACK_TERMS,
                    max_total_tokens=MAX_FALLBACK_TOKEN_BUDGET,
                    include_date=False,
                ),
            ),
            (
                "abstract-only",
                self._build_field_specific_cql(
                    field="ab",
                    jurisdictions=jurisdictions,
                    start_date=start_date,
                    end_date=end_date,
                    positive_keywords=positive_keywords or [],
                    max_positive_terms=MAX_FALLBACK_TERMS,
                    max_total_tokens=MAX_FALLBACK_TOKEN_BUDGET,
                    include_date=False,
                ),
            ),
        ]

        if positive_keywords:
            field_results: Dict[str, Dict[str, Any]] = {}
            for strategy_name, field_cql in field_payloads:
                field_payload: Dict[str, Any] = {
                    "cql": field_cql,
                    "limit": limit or 100,
                    "offset": 1,
                }
                try:
                    field_result = await self.search_patents(field_payload)
                    field_results[strategy_name] = field_result
                    strategy_attempts.append(
                        {
                            "strategy": strategy_name,
                            "query": field_payload.get("cql"),
                            "endpoint_used": field_result.get("endpoint_used"),
                            "endpoint_attempts": field_result.get("endpoint_attempts", []),
                            "raw_entry_count": field_result.get("raw_entry_count"),
                            "normalized_count": field_result.get("normalized_count"),
                            "total_available": field_result.get("total_available"),
                        }
                    )
                except Exception as field_exc:
                    strategy_attempts.append(
                        {
                            "strategy": strategy_name,
                            "query": field_payload.get("cql"),
                            "error": str(field_exc),
                        }
                    )

            merged_field_records = self._merge_records_by_id(
                [
                    field_results.get("title-only", {}).get("data", []),
                    field_results.get("abstract-only", {}).get("data", []),
                ]
            )

            if merged_field_records:
                result = {
                    "data": merged_field_records,
                    "total": len(merged_field_records),
                    "provider": "epo",
                    "query": "field-split:title+abstract",
                    "query_strategy": "field-split-title-abstract",
                    "field_search_mode": "union",
                }

                title_endpoint = field_results.get("title-only", {}).get("endpoint_used")
                abstract_endpoint = field_results.get("abstract-only", {}).get("endpoint_used")
                result["endpoint_used"] = title_endpoint or abstract_endpoint

                result["field_query_details"] = {
                    "title": {
                        "query": field_payloads[0][1],
                        "endpoint_used": title_endpoint,
                        "count": len(field_results.get("title-only", {}).get("data", [])),
                    },
                    "abstract": {
                        "query": field_payloads[1][1],
                        "endpoint_used": abstract_endpoint,
                        "count": len(field_results.get("abstract-only", {}).get("data", [])),
                    },
                }

        try:
            if not result.get("data"):
                result = await self.search_patents(query_payload)
                strategy_attempts.append(
                    {
                        "strategy": "primary",
                        "query": query_payload.get("cql"),
                        "endpoint_used": result.get("endpoint_used"),
                        "raw_entry_count": result.get("raw_entry_count"),
                        "normalized_count": result.get("normalized_count"),
                        "total_available": result.get("total_available"),
                    }
                )
        except EPOAPIError as exc:
            message = str(exc)
            if (
                "CLIENT.CQLSyntax" not in message
                and "CLIENT.MaximumTotalTerms" not in message
            ):
                raise

            strategy_attempts.append(
                {
                    "strategy": "primary",
                    "query": query_payload.get("cql"),
                    "error": message,
                }
            )

            logger.warning(
                "EPO query rejected. Retrying with simplified CQL. Error: %s",
                message,
            )

            fallback_cql = self._build_ops_cql(
                jurisdictions=jurisdictions,
                start_date=start_date,
                end_date=end_date,
                positive_keywords=positive_keywords or [],
                negative_keywords=negative_keywords or [],
                max_positive_terms=MAX_FALLBACK_TERMS,
                max_total_tokens=MAX_FALLBACK_TOKEN_BUDGET,
                include_negative=False,
                include_date=False,
            )
            logger.debug("EPO simplified CQL: %s", fallback_cql)

            fallback_payload: Dict[str, Any] = {
                "cql": fallback_cql,
                "limit": limit or 100,
                "offset": 1,
            }
            result = await self.search_patents(fallback_payload)
            strategy_attempts.append(
                {
                    "strategy": "simplified-cql",
                    "query": fallback_payload.get("cql"),
                    "endpoint_used": result.get("endpoint_used"),
                    "endpoint_attempts": result.get("endpoint_attempts", []),
                    "raw_entry_count": result.get("raw_entry_count"),
                    "normalized_count": result.get("normalized_count"),
                    "total_available": result.get("total_available"),
                }
            )

        # If still too many terms for OPS limits, retry with an even smaller query.
        if not result.get("data") and (positive_keywords or []):
            aggressive_cql = self._build_ops_cql(
                jurisdictions=jurisdictions,
                start_date=start_date,
                end_date=end_date,
                positive_keywords=positive_keywords or [],
                negative_keywords=[],
                max_positive_terms=2,
                max_total_tokens=6,
                include_negative=False,
                include_date=False,
            )
            aggressive_payload: Dict[str, Any] = {
                "cql": aggressive_cql,
                "limit": limit or 100,
                "offset": 1,
            }
            try:
                aggressive_result = await self.search_patents(aggressive_payload)
                strategy_attempts.append(
                    {
                        "strategy": "aggressive-term-budget",
                        "query": aggressive_payload.get("cql"),
                        "endpoint_used": aggressive_result.get("endpoint_used"),
                        "endpoint_attempts": aggressive_result.get("endpoint_attempts", []),
                        "raw_entry_count": aggressive_result.get("raw_entry_count"),
                        "normalized_count": aggressive_result.get("normalized_count"),
                        "total_available": aggressive_result.get("total_available"),
                    }
                )
                if aggressive_result.get("data"):
                    result = aggressive_result
                    result["query_strategy"] = "aggressive-term-budget"
            except Exception as aggressive_exc:
                strategy_attempts.append(
                    {
                        "strategy": "aggressive-term-budget",
                        "query": aggressive_payload.get("cql"),
                        "error": str(aggressive_exc),
                    }
                )

        probe_diagnostics: List[Dict[str, Any]] = []
        if not result.get("data") and (positive_keywords or []):
            probe_diagnostics, probe_records = await self._probe_positive_terms(
                jurisdictions=jurisdictions,
                start_date=start_date,
                end_date=end_date,
                positive_keywords=positive_keywords or [],
                limit=limit,
            )
            if probe_records:
                logger.info(
                    "EPO probe fallback recovered %s records after zero-result primary query.",
                    len(probe_records),
                )
                result["data"] = probe_records
                result["query_strategy"] = "probe-fallback"
            else:
                result["query_strategy"] = "primary-zero-result"

        if not result.get("data") and (positive_keywords or []):
            relaxed_cql = self._build_relaxed_unfielded_cql(positive_keywords or [])
            relaxed_payload: Dict[str, Any] = {
                "cql": relaxed_cql,
                "limit": limit or 100,
                "offset": 1,
            }
            try:
                relaxed_result = await self.search_patents(relaxed_payload)
                strategy_attempts.append(
                    {
                        "strategy": "relaxed-unfielded",
                        "query": relaxed_payload.get("cql"),
                        "endpoint_used": relaxed_result.get("endpoint_used"),
                        "endpoint_attempts": relaxed_result.get("endpoint_attempts", []),
                        "raw_entry_count": relaxed_result.get("raw_entry_count"),
                        "normalized_count": relaxed_result.get("normalized_count"),
                        "total_available": relaxed_result.get("total_available"),
                    }
                )
                if relaxed_result.get("data"):
                    result = relaxed_result
                    result["query_strategy"] = "relaxed-unfielded"
            except Exception as relaxed_exc:
                strategy_attempts.append(
                    {
                        "strategy": "relaxed-unfielded",
                        "query": relaxed_payload.get("cql"),
                        "error": str(relaxed_exc),
                    }
                )

        if not result.get("data") and (positive_keywords or []):
            ta_cql = self._build_relaxed_ta_cql(positive_keywords or [])
            ta_payload: Dict[str, Any] = {
                "cql": ta_cql,
                "limit": limit or 100,
                "offset": 1,
            }
            try:
                ta_result = await self.search_patents(ta_payload)
                strategy_attempts.append(
                    {
                        "strategy": "relaxed-ta",
                        "query": ta_payload.get("cql"),
                        "endpoint_used": ta_result.get("endpoint_used"),
                        "endpoint_attempts": ta_result.get("endpoint_attempts", []),
                        "raw_entry_count": ta_result.get("raw_entry_count"),
                        "normalized_count": ta_result.get("normalized_count"),
                        "total_available": ta_result.get("total_available"),
                    }
                )
                if ta_result.get("data"):
                    result = ta_result
                    result["query_strategy"] = "relaxed-ta"
            except Exception as ta_exc:
                strategy_attempts.append(
                    {
                        "strategy": "relaxed-ta",
                        "query": ta_payload.get("cql"),
                        "error": str(ta_exc),
                    }
                )

        if not result.get("data") and (positive_keywords or []):
            bare_cql = self._build_relaxed_bare_or_cql(positive_keywords or [])
            bare_payload: Dict[str, Any] = {
                "cql": bare_cql,
                "limit": limit or 100,
                "offset": 1,
            }
            try:
                bare_result = await self.search_patents(bare_payload)
                strategy_attempts.append(
                    {
                        "strategy": "relaxed-bare-or",
                        "query": bare_payload.get("cql"),
                        "endpoint_used": bare_result.get("endpoint_used"),
                        "endpoint_attempts": bare_result.get("endpoint_attempts", []),
                        "raw_entry_count": bare_result.get("raw_entry_count"),
                        "normalized_count": bare_result.get("normalized_count"),
                        "total_available": bare_result.get("total_available"),
                    }
                )
                if bare_result.get("data"):
                    result = bare_result
                    result["query_strategy"] = "relaxed-bare-or"
            except Exception as bare_exc:
                strategy_attempts.append(
                    {
                        "strategy": "relaxed-bare-or",
                        "query": bare_payload.get("cql"),
                        "error": str(bare_exc),
                    }
                )

        data = result.get("data", [])
        filtered = self._apply_negative_keyword_filter(data, negative_keywords)
        result["data"] = filtered
        result["pre_filter_total"] = len(data)
        result["filtered_total"] = len(filtered)
        result["probe_diagnostics"] = probe_diagnostics
        result["strategy_attempts"] = strategy_attempts

        logger.info(
            "✅ Completed EPO search with %s results (%s after negative filters)",
            len(data),
            len(filtered),
        )
        return result

    async def _probe_positive_terms(
        self,
        *,
        jurisdictions: Optional[List[str]],
        start_date: Optional[str],
        end_date: Optional[str],
        positive_keywords: List[str],
        limit: Optional[int],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Probe individual positive terms to identify over-restrictive composite queries.

        Returns:
            Tuple of (probe diagnostics list, merged unique records list).
        """
        diagnostics: List[Dict[str, Any]] = []
        merged_records: Dict[str, Dict[str, Any]] = {}

        probe_terms = self._clip_terms(positive_keywords, max_terms=MAX_FALLBACK_TERMS)
        for term in probe_terms:
            probe_cql = self._build_ops_cql(
                jurisdictions=jurisdictions,
                start_date=start_date,
                end_date=end_date,
                positive_keywords=[term],
                negative_keywords=[],
                max_positive_terms=1,
                include_negative=False,
                include_date=False,
            )
            payload = {
                "cql": probe_cql,
                "limit": min(limit or 100, 25),
                "offset": 1,
            }
            try:
                probe_result = await self.search_patents(payload)
                records = probe_result.get("data", [])
                for record in records:
                    record_id = record.get("record_id")
                    if record_id and record_id not in merged_records:
                        merged_records[record_id] = record

                diagnostics.append(
                    {
                        "term": term,
                        "query": probe_cql,
                        "total_available": probe_result.get("total_available"),
                        "raw_entry_count": probe_result.get("raw_entry_count"),
                        "normalized_count": probe_result.get("normalized_count"),
                    }
                )
            except Exception as exc:
                diagnostics.append(
                    {
                        "term": term,
                        "query": probe_cql,
                        "error": str(exc),
                    }
                )

        return diagnostics, list(merged_records.values())

    async def get_patent_by_epo_id(self, epo_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific patent by EPO DOCDB-style identifier.

        Args:
            epo_id: Provider-specific EPO document identifier.

        Returns:
            Patent record if found; otherwise `None`.
        """
        if not epo_id:
            return None

        query_payload = {
            "cql": f'pn="{self._escape_cql_term(epo_id)}"',
            "limit": 1,
            "offset": 1,
        }
        result = await self.search_patents(query_payload)
        records = result.get("data", [])
        return records[0] if records else None

    async def get_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Generic identifier lookup helper for provider-neutral service code.

        Args:
            identifier: Provider-specific record identifier (`epo_id` for EPO).

        Returns:
            Patent record or `None`.
        """
        return await self.get_patent_by_epo_id(identifier)

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a lightweight OPS connectivity health check.

        This check validates credential presence and OAuth token retrieval
        without executing a full patent search query.

        Returns:
            Dictionary containing health status details.
        """
        if not self.consumer_key or not self.consumer_secret:
            return {
                "provider": "epo",
                "ok": False,
                "message": "Missing EPO consumer credentials.",
            }

        try:
            token = await self._get_access_token(force_refresh=True)
            return {
                "provider": "epo",
                "ok": bool(token),
                "message": "EPO OAuth token retrieved successfully.",
            }
        except Exception as exc:
            return {
                "provider": "epo",
                "ok": False,
                "message": str(exc),
            }

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
    def _clip_terms(terms: List[str], max_terms: int) -> List[str]:
        """Return a sanitized, bounded list of non-empty keyword terms."""
        output: List[str] = []
        for term in terms:
            if len(output) >= max_terms:
                break
            if not term:
                continue
            value = EPOConnector._escape_cql_term(term)
            if value:
                output.append(value)
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
        include_negative: bool = True,
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

        positive_terms = self._clip_terms(positive_keywords, max_positive_terms)
        negative_terms = self._clip_terms(negative_keywords, max_positive_terms)

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
            return {}

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

        provider_record_url = None
        for link in entry.findall(self._namespace_wild("link")):
            href = link.attrib.get("href")
            if href:
                provider_record_url = href
                break

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
        }

        url = f"{self.base_url}/published-data/search"
        timeout = float(self.config.epo_request_timeout_seconds)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    url,
                    params={"q": cql, "Range": f"{offset}-{range_end}"},
                    headers=headers,
                )

                if response.status_code == 401:
                    refreshed = await self._get_access_token(force_refresh=True)
                    headers["Authorization"] = f"Bearer {refreshed}"
                    response = await client.get(
                        url,
                        params={"q": cql, "Range": f"{offset}-{range_end}"},
                        headers=headers,
                    )

                if response.status_code == 429:
                    raise EPORateLimitError("EPO OPS rate limit exceeded.")
                if response.status_code != 200:
                    raise EPOAPIError(
                        f"EPO search error {response.status_code}: {response.text}"
                    )

            root = ET.fromstring(response.text)
            entries = root.findall(self._namespace_wild("entry"))
            if not entries:
                # Some OPS responses may nest entries under atom feed path.
                entries = root.findall(self._namespace_wild("feed/entry"))

            records = [self._normalize_entry(entry) for entry in entries]
            records = [r for r in records if r]

            return {
                "data": records,
                "total": len(records),
                "provider": "epo",
                "query": cql,
            }
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
        try:
            result = await self.search_patents(query_payload)
        except EPOAPIError as exc:
            message = str(exc)
            if "CLIENT.CQLSyntax" not in message:
                raise

            logger.warning(
                "EPO CQL syntax rejected. Retrying with simplified CQL. Error: %s",
                message,
            )

            fallback_cql = self._build_ops_cql(
                jurisdictions=jurisdictions,
                start_date=start_date,
                end_date=end_date,
                positive_keywords=positive_keywords or [],
                negative_keywords=negative_keywords or [],
                max_positive_terms=MAX_FALLBACK_TERMS,
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

        data = result.get("data", [])
        filtered = self._apply_negative_keyword_filter(data, negative_keywords)
        result["data"] = filtered
        result["filtered_total"] = len(filtered)

        logger.info(
            "✅ Completed EPO search with %s results (%s after negative filters)",
            len(data),
            len(filtered),
        )
        return result

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

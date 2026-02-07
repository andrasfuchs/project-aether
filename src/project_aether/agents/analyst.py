"""
Analyst Agent for Project Aether.
Performs forensic analysis, semantic scoring, and classification of patent data.
Based on implementation plan Section 4.1.3.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from project_aether.tools.inpadoc import (
    analyze_legal_status,
    StatusAnalysis,
    StatusSeverity,
)
from project_aether.core.keywords import DEFAULT_KEYWORDS, get_flattened_keywords

logger = logging.getLogger("AnalystAgent")


def _safe_get_nested(data: Dict, path: str, default: Any = None) -> Any:
    """
    Safely extract nested field from dictionary using dot notation.
    
    Args:
        data: Dictionary to extract from
        path: Dot-separated path (e.g., 'biblio.invention_title')
        default: Default value if path not found
        
    Returns:
        Extracted value or default
    """
    keys = path.split('.')
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default
    return current if current is not None else default


@dataclass
class PatentAssessment:
    """
    Complete assessment of a patent's intelligence value.
    """
    lens_id: str
    jurisdiction: str
    doc_number: str
    title: str
    inventors: List[str]  # List of inventor names
    
    # Legal analysis
    status_analysis: StatusAnalysis
    
    # Semantic analysis
    relevance_score: float  # 0-100
    is_anomalous: bool
    classification_tags: List[str]
    
    # Summary
    intelligence_value: str  # "HIGH", "MEDIUM", "LOW"
    summary: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "lens_id": self.lens_id,
            "jurisdiction": self.jurisdiction,
            "doc_number": self.doc_number,
            "title": self.title,
            "inventors": self.inventors,
            "status_analysis": self.status_analysis.to_dict(),
            "relevance_score": self.relevance_score,
            "is_anomalous": self.is_anomalous,
            "classification_tags": self.classification_tags,
            "intelligence_value": self.intelligence_value,
            "summary": self.summary,
        }


class AnalystAgent:
    """
    The Domain Expert Agent.
    Performs forensic analysis and semantic scoring of patent data.

     Parameters
     ----------
     keyword_config : Optional[Dict]
          Optional language-keyed keyword configuration. When provided, the agent
          flattens this structure into two lists via `get_flattened_keywords()`:
          - `anomalous_keywords`: terms indicating anomalous phenomena
          - `false_positive_keywords`: terms indicating conventional technology
          If omitted, `DEFAULT_KEYWORDS` are used.

     Working Methods (Pipeline)
     --------------------------
     1) Legal Status Forensics
         Uses `analyze_legal_status()` to interpret jurisdiction-specific
         INPADOC event codes and patent status. This produces `StatusAnalysis`
         with a `severity` of `HIGH`, `MEDIUM`, `LOW`, or `UNKNOWN` based on
         refusal/withdrawal/lapse semantics from the INPADOC code database.

     2) Relevance Score Calculation (0-100)
         Computed in `_calculate_relevance_score(text)` using simple keyword
         matching on lowercased title + abstract + claims:

         - +15 points per anomalous keyword hit
         - -20 points per false-positive keyword hit
         - +10 points if "hydrogen" or "deuterium" present
         - +10 points if "plasma" or "discharge" present

         The final score is clamped to the range $[0, 100]$.

     3) Anomalous Flag
         `_is_anomalous_content(text)` returns True if any anomalous keyword is
         present, or if "over-unity"/"excess" appears alongside "energy"/"heat".

     4) Classification Tag Extraction
         `_extract_classification_tags(patent_record)` inspects IPC/CPC symbols
         under `biblio.classifications_ipcr` and `biblio.classifications_cpc`.
         Any symbol containing a high-value classification marker in
         `self.high_value_classifications` is added to `classification_tags`.

     5) Intelligence Value Decision
         `_determine_intelligence_value(...)` applies rule-based thresholds:
         - HIGH: severity HIGH + relevance >= 50 + anomalous, OR any high-value
            classification with severity HIGH.
         - MEDIUM: relevance >= 40 + anomalous, OR severity HIGH with low relevance.
         - LOW: default fallback.
    """
    
    def __init__(self, keyword_config: Optional[Dict] = None):
        self.logger = logger
        
        if keyword_config:
            self.anomalous_keywords, self.false_positive_keywords = get_flattened_keywords(keyword_config)
        else:
            self.anomalous_keywords, self.false_positive_keywords = get_flattened_keywords(DEFAULT_KEYWORDS)
        
        # High-value IPC/CPC classifications
        self.high_value_classifications = {
            "G21B 3/00",  # Low temperature nuclear fusion
            "H01J 37/00", # Discharge tubes
            "H05H 1/00",  # Plasma technique
            "C25B 1/00",  # Electrolytic production
        }
    
    def analyze_patent(self, patent_record: Dict) -> PatentAssessment:
        """
        Perform complete analysis of a single patent.
        
        Args:
            patent_record: Patent data from Lens.org API
                          May include pre-translated fields: title_en, abstract_en, claims_en
            
        Returns:
            PatentAssessment with complete analysis
        """
        # Extract basic info
        lens_id = patent_record.get("lens_id", "UNKNOWN")
        jurisdiction = patent_record.get("jurisdiction", "UNKNOWN")
        doc_number = patent_record.get("doc_number", "UNKNOWN")
        
        # Extract title from nested structure (always use original, not translation)
        title_data = _safe_get_nested(patent_record, "biblio.invention_title")
        if isinstance(title_data, list) and len(title_data) > 0:
            title = title_data[0].get("text", "Untitled") if isinstance(title_data[0], dict) else str(title_data[0])
        elif isinstance(title_data, str):
            title = title_data
        else:
            title = "Untitled"
        
        # Extract inventors from nested structure
        inventors_data = _safe_get_nested(patent_record, "biblio.parties.inventors", [])
        inventors = []
        
        if isinstance(inventors_data, list):
            for inv in inventors_data:
                if isinstance(inv, dict):
                    # Try multiple fields where name might be
                    name = None
                    if "extracted_name" in inv and isinstance(inv["extracted_name"], dict):
                        name = inv["extracted_name"].get("value")  # Changed from 'name' to 'value'
                    if not name:
                        name = inv.get("name")
                    if not name:
                        name = inv.get("full_name")
                    if name and isinstance(name, str):
                        inventors.append(name)
        
        logger.info(f"🔬 Analyzing patent: {lens_id} ({jurisdiction}) - Inventors found: {inventors}")
        
        # 1. Legal Status Forensics
        status_analysis = analyze_legal_status(patent_record)
        
        # 2. Semantic Analysis
        # Extract and use English versions when available
        
        # Extract abstract (prefer English translation if available)
        abstract_data = patent_record.get("abstract_en")
        if not abstract_data:
            abstract_data = patent_record.get("abstract", "")
        if isinstance(abstract_data, list) and len(abstract_data) > 0:
            abstract = abstract_data[0].get("text", "") if isinstance(abstract_data[0], dict) else str(abstract_data[0])
        else:
            abstract = str(abstract_data) if abstract_data else ""
        
        # Extract claims (prefer English translation if available)
        claims_data = patent_record.get("claims_en")
        if not claims_data:
            claims_data = patent_record.get("claims", "")
        if isinstance(claims_data, list) and len(claims_data) > 0:
            claims = claims_data[0].get("text", "") if isinstance(claims_data[0], dict) else str(claims_data[0])
        else:
            claims = str(claims_data) if claims_data else ""
        
        full_text = f"{title} {abstract} {claims}".lower()
        
        relevance_score = self._calculate_relevance_score(full_text)
        is_anomalous = self._is_anomalous_content(full_text)
        classification_tags = self._extract_classification_tags(patent_record)

        
        # 3. Determine Intelligence Value
        intelligence_value = self._determine_intelligence_value(
            status_analysis,
            relevance_score,
            is_anomalous,
            classification_tags,
        )
        
        # 4. Generate Summary
        summary = self._generate_summary(
            status_analysis,
            relevance_score,
            is_anomalous,
            classification_tags,
        )
        
        return PatentAssessment(
            lens_id=lens_id,
            jurisdiction=jurisdiction,
            doc_number=doc_number,
            title=title,
            inventors=inventors,
            status_analysis=status_analysis,
            relevance_score=relevance_score,
            is_anomalous=is_anomalous,
            classification_tags=classification_tags,
            intelligence_value=intelligence_value,
            summary=summary,
        )
    
    def _calculate_relevance_score(self, text: str) -> float:
        """
        Calculate relevance score based on keyword presence.
        Simple keyword matching (can be replaced with LLM-based scoring later).
        
        Args:
            text: Combined patent text (title + abstract + claims)
            
        Returns:
            Score from 0-100
        """
        score = 0.0
        
        # Check for anomalous keywords (high value)
        anomalous_hits = sum(
            1 for keyword in self.anomalous_keywords
            if keyword.lower() in text
        )
        score += anomalous_hits * 15  # 15 points per anomalous keyword
        
        # Check for false positive keywords (negative points)
        false_positive_hits = sum(
            1 for keyword in self.false_positive_keywords
            if keyword.lower() in text
        )
        score -= false_positive_hits * 20  # -20 points per false positive
        
        # General hydrogen + plasma/spark presence (baseline)
        if "hydrogen" in text or "deuterium" in text:
            score += 10
        if "plasma" in text or "discharge" in text:
            score += 10
        
        # Clamp to 0-100 range
        return max(0.0, min(100.0, score))
    
    def _is_anomalous_content(self, text: str) -> bool:
        """
        Determine if content describes anomalous phenomena.
        
        Args:
            text: Combined patent text
            
        Returns:
            True if anomalous content detected
        """
        # Check if any anomalous keywords present
        for keyword in self.anomalous_keywords:
            if keyword.lower() in text:
                return True
        
        # Check for over-unity claims
        if "over-unity" in text or "excess" in text:
            if "energy" in text or "heat" in text:
                return True
        
        return False
    
    def _extract_classification_tags(self, patent_record: Dict) -> List[str]:
        """
        Extract relevant IPC/CPC classification tags.
        
        Args:
            patent_record: Patent data
            
        Returns:
            List of relevant classification codes
        """
        tags = []
        
        # Check IPC classifications (nested in biblio)
        ipcr = _safe_get_nested(patent_record, "biblio.classifications_ipcr", [])
        for classification in ipcr:
            if isinstance(classification, dict):
                symbol = classification.get("symbol", "")
                # Extract main group (e.g., "G21B 3/00")
                if any(hv in symbol for hv in self.high_value_classifications):
                    tags.append(symbol)
        
        # Check CPC classifications (nested in biblio)
        cpc = _safe_get_nested(patent_record, "biblio.classifications_cpc", [])
        for classification in cpc:
            if isinstance(classification, dict):
                symbol = classification.get("symbol", "")
                if any(hv in symbol for hv in self.high_value_classifications):
                    tags.append(symbol)
        
        return list(set(tags))  # Remove duplicates
    
    def _determine_intelligence_value(
        self,
        status_analysis: StatusAnalysis,
        relevance_score: float,
        is_anomalous: bool,
        classification_tags: List[str],
    ) -> str:
        """
        Determine overall intelligence value of the patent.
        
        Returns:
            "HIGH", "MEDIUM", or "LOW"
        """
        # High priority: substantive rejection + high relevance + anomalous
        if (
            status_analysis.severity == StatusSeverity.HIGH
            and relevance_score >= 50
            and is_anomalous
        ):
            return "HIGH"
        
        # High priority: high-value classification regardless of score
        if classification_tags and status_analysis.severity == StatusSeverity.HIGH:
            return "HIGH"
        
        # Medium priority: good relevance but not refused
        if relevance_score >= 40 and is_anomalous:
            return "MEDIUM"
        
        # Medium priority: refused but low relevance
        if status_analysis.severity == StatusSeverity.HIGH:
            return "MEDIUM"
        
        # Default to low
        return "LOW"
    
    def _generate_summary(
        self,
        status_analysis: StatusAnalysis,
        relevance_score: float,
        is_anomalous: bool,
        classification_tags: List[str],
    ) -> str:
        """
        Generate human-readable summary of the analysis.
        
        Returns:
            Summary string
        """
        parts = []
        
        # Legal status summary
        if status_analysis.is_refused:
            parts.append(f"🚨 Substantively refused: {status_analysis.refusal_reason}")
        elif status_analysis.is_withdrawn:
            parts.append(f"⚠️ Withdrawn by applicant")
        else:
            parts.append(f"ℹ️ {status_analysis.interpretation}")
        
        # Relevance summary
        if relevance_score >= 70:
            parts.append(f"📊 High relevance score: {relevance_score:.0f}/100")
        elif relevance_score >= 40:
            parts.append(f"📊 Moderate relevance: {relevance_score:.0f}/100")
        else:
            parts.append(f"📊 Low relevance: {relevance_score:.0f}/100")
        
        # Anomalous flag
        if is_anomalous:
            parts.append("⚡ Contains anomalous phenomena terminology")
        
        # Classifications
        if classification_tags:
            parts.append(f"🏷️ High-value classifications: {', '.join(classification_tags)}")
        
        return " | ".join(parts)
    
    def analyze_batch(self, patent_records: List[Dict]) -> List[PatentAssessment]:
        """
        Analyze multiple patents in batch.
        
        Args:
            patent_records: List of patent records from Lens.org
            
        Returns:
            List of PatentAssessment objects
        """
        assessments = []
        
        for record in patent_records:
            try:
                assessment = self.analyze_patent(record)
                assessments.append(assessment)
                
                if assessment.intelligence_value == "HIGH":
                    logger.info(
                        f"🎯 HIGH VALUE TARGET: {assessment.lens_id} "
                        f"({assessment.jurisdiction}) - {assessment.summary}"
                    )
            except Exception as e:
                logger.error(f"Failed to analyze patent: {e}")
        
        return assessments
    
    def filter_high_priority(
        self,
        assessments: List[PatentAssessment]
    ) -> List[PatentAssessment]:
        """
        Filter only high-priority assessments.
        
        Args:
            assessments: List of all assessments
            
        Returns:
            List of high-priority assessments only
        """
        return [a for a in assessments if a.intelligence_value == "HIGH"]


# Convenience function for agent graph integration
async def analyze_batch(state: Dict) -> Dict:
    """
    Agent node function for LangGraph integration.
    Analyzes patents from the state.
    
    Args:
        state: Mission state with raw_patents
        
    Returns:
        Updated state with analyzed_artifacts
    """
    raw_patents = state.get("raw_patents", [])
    
    if not raw_patents:
        logger.warning("No patents to analyze")
        return {"analyzed_artifacts": []}
    
    analyst = AnalystAgent()
    assessments = analyst.analyze_batch(raw_patents)
    
    # Convert to dict format for state
    artifacts = [a.to_dict() for a in assessments]
    
    return {"analyzed_artifacts": artifacts}

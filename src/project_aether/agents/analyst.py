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


@dataclass
class PatentAssessment:
    """
    Complete assessment of a patent's intelligence value.
    """
    lens_id: str
    jurisdiction: str
    doc_number: str
    title: str
    
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
            
        Returns:
            PatentAssessment with complete analysis
        """
        # Extract basic info
        lens_id = patent_record.get("lens_id", "UNKNOWN")
        jurisdiction = patent_record.get("jurisdiction", "UNKNOWN")
        doc_number = patent_record.get("doc_number", "UNKNOWN")
        title = patent_record.get("title", "Untitled")
        
        logger.info(f"🔬 Analyzing patent: {lens_id} ({jurisdiction})")
        
        # 1. Legal Status Forensics
        status_analysis = analyze_legal_status(patent_record)
        
        # 2. Semantic Analysis
        abstract = patent_record.get("abstract", "")
        claims = patent_record.get("claims", "")
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
        
        # Check IPC classifications
        ipcr = patent_record.get("classifications_ipcr", [])
        for classification in ipcr:
            symbol = classification.get("symbol", "")
            # Extract main group (e.g., "G21B 3/00")
            if any(hv in symbol for hv in self.high_value_classifications):
                tags.append(symbol)
        
        # Check CPC classifications
        cpc = patent_record.get("classifications_cpc", [])
        for classification in cpc:
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

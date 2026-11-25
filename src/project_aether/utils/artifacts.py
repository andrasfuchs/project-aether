"""
Artifact generation utilities for Project Aether.
Creates structured, interactive state objects for the Streamlit UI.
Based on implementation plan Section 4.3.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger("Artifacts")


def _safe_get_nested(data: dict, path: str, default: Any = None) -> Any:
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
class DashboardArtifact:
    """
    Weekly mission statistics artifact.
    Rendered as metrics in the Streamlit UI.
    """
    mission_id: str
    date_generated: str
    
    # Statistics
    total_patents_searched: int
    rejections_found: int
    withdrawals_found: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    
    # Jurisdictions
    jurisdictions_searched: list[str]
    
    # Top findings
    top_jurisdiction: str | None = None
    anomalous_count: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class ReviewArtifact:
    """
    Detailed patent review list artifact.
    Rendered as an interactive data grid in Streamlit.
    """
    patents: list[dict[str, Any]]
    total_count: int
    filter_applied: str | None = None
    sort_by: str = "intelligence_value"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "patents": self.patents,
            "total_count": self.total_count,
            "filter_applied": self.filter_applied,
            "sort_by": self.sort_by,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class AnalysisArtifact:
    """
    Detailed analysis of a single patent.
    Rendered as a markdown report with diagrams.
    """
    record_id: str
    lens_id: str | None
    epo_id: str | None
    provider_name: str
    provider_record_url: str | None
    patent_number: str
    jurisdiction: str
    title: str
    
    # Analysis details
    status_summary: str
    relevance_score: float
    intelligence_value: str
    classification_tags: list[str]
    
    # Full text
    abstract: str
    rejection_reason: str
    
    # Metadata
    applicants: list[str]
    inventors: list[str]
    date_published: str | None = None
    date_discontinued: str | None = None
    
    # Relations
    related_patents: list[dict[str, str]] = None
    
    def __post_init__(self):
        if self.related_patents is None:
            self.related_patents = []
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_markdown(self) -> str:
        """
        Generate a markdown report for this patent.
        
        Returns:
            Markdown-formatted report
        """
        lines = [
            f"# Analysis: {self.title}",
            "",
            f"**Record ID:** {self.record_id}  ",
            f"**Provider:** {self.provider_name.upper()}  ",
            f"**Lens ID:** {self.lens_id or 'N/A'}  ",
            f"**EPO ID:** {self.epo_id or 'N/A'}  ",
            f"**Patent Number:** {self.patent_number}  ",
            f"**Jurisdiction:** {self.jurisdiction}  ",
            f"**Intelligence Value:** {self.intelligence_value}  ",
            f"**Relevance Score:** {self.relevance_score:.1f}/100  ",
            "",
            "## 🔍 Status Analysis",
            "",
            self.status_summary,
            "",
            f"**Rejection Reason:** {self.rejection_reason}",
            "",
            "## 📄 Abstract",
            "",
            self.abstract,
            "",
            "## 🏷️ Classifications",
            "",
        ]
        
        if self.classification_tags:
            for tag in self.classification_tags:
                lines.append(f"- {tag}")
        else:
            lines.append("*No high-value classifications identified*")
        
        lines.extend([
            "",
            "## 👥 People & Organizations",
            "",
            "**Applicants:**",
        ])
        
        for applicant in self.applicants:
            lines.append(f"- {applicant}")
        
        lines.append("")
        lines.append("**Inventors:**")
        
        for inventor in self.inventors:
            lines.append(f"- {inventor}")
        
        if self.related_patents:
            lines.extend([
                "",
                "## 🔗 Related Patents",
                "",
            ])
            
            for related in self.related_patents:
                lines.append(
                    f"- [{related['number']}] {related['title']} "
                    f"({related['jurisdiction']})"
                )
        
        lines.extend([
            "",
            "## 📅 Timeline",
            "",
            f"- **Published:** {self.date_published or 'Unknown'}",
            f"- **Discontinued:** {self.date_discontinued or 'Unknown'}",
            f"- **Provider Record URL:** {self.provider_record_url or 'Unavailable'}",
            "",
            "---",
            "",
            "*Generated by Project Aether*",
        ])
        
        return "\n".join(lines)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)


class ArtifactGenerator:
    """
    Utility class for generating artifacts from raw data.
    """
    
    def __init__(self, mission_id: str | None = None):
        """
        Initialize the artifact generator.
        
        Args:
            mission_id: Optional mission ID. Auto-generated if not provided.
        """
        self.mission_id = mission_id or self._generate_mission_id()
        self.logger = logger
    
    def _generate_mission_id(self) -> str:
        """Generate a unique mission ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"MISSION_{timestamp}"
    
    def create_dashboard_artifact(
        self,
        assessments: list[dict[str, Any]],
        jurisdictions: list[str],
    ) -> DashboardArtifact:
        """
        Create a dashboard artifact from patent assessments.
        
        Args:
            assessments: List of patent assessments
            jurisdictions: Jurisdictions searched
            
        Returns:
            DashboardArtifact
        """
        # Calculate statistics
        total_patents = len(assessments)
        
        high_priority = sum(
            1 for a in assessments
            if a.get("intelligence_value") == "HIGH"
        )
        medium_priority = sum(
            1 for a in assessments
            if a.get("intelligence_value") == "MEDIUM"
        )
        low_priority = sum(
            1 for a in assessments
            if a.get("intelligence_value") == "LOW"
        )
        
        rejections = sum(
            1 for a in assessments
            if a.get("status_analysis", {}).get("is_refused", False)
        )
        withdrawals = sum(
            1 for a in assessments
            if a.get("status_analysis", {}).get("is_withdrawn", False)
        )
        
        anomalous = sum(
            1 for a in assessments
            if a.get("is_anomalous", False)
        )
        
        # Find top jurisdiction
        jurisdiction_counts = {}
        for assessment in assessments:
            jur = assessment.get("jurisdiction", "UNKNOWN")
            jurisdiction_counts[jur] = jurisdiction_counts.get(jur, 0) + 1
        
        top_jurisdiction = (
            max(jurisdiction_counts.items(), key=lambda x: x[1])[0]
            if jurisdiction_counts
            else None
        )
        
        artifact = DashboardArtifact(
            mission_id=self.mission_id,
            date_generated=datetime.now().isoformat(),
            total_patents_searched=total_patents,
            rejections_found=rejections,
            withdrawals_found=withdrawals,
            high_priority_count=high_priority,
            medium_priority_count=medium_priority,
            low_priority_count=low_priority,
            jurisdictions_searched=jurisdictions,
            top_jurisdiction=top_jurisdiction,
            anomalous_count=anomalous,
        )
        
        #logger.info(f"Created dashboard artifact for {self.mission_id}")
        return artifact
    
    def create_review_artifact(
        self,
        assessments: list[dict[str, Any]],
        filter_level: str | None = None,
    ) -> ReviewArtifact:
        """
        Create a review artifact from patent assessments.
        
        Args:
            assessments: List of patent assessments
            filter_level: Optional filter (e.g., "HIGH", "MEDIUM")
            
        Returns:
            ReviewArtifact
        """
        # Apply filter if specified
        if filter_level:
            filtered = [
                a for a in assessments
                if a.get("intelligence_value") == filter_level
            ]
        else:
            filtered = assessments
        
        # Sort by intelligence value
        sorted_patents = sorted(
            filtered,
            key=lambda x: (
                {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(
                    x.get("intelligence_value", "LOW"), 0
                )
            ),
            reverse=True,
        )
        
        artifact = ReviewArtifact(
            patents=sorted_patents,
            total_count=len(sorted_patents),
            filter_applied=filter_level,
            sort_by="intelligence_value",
        )
        
        logger.info(
            f"📋 Created review artifact with {len(sorted_patents)} patents"
        )
        return artifact
    
    def create_deep_dive_artifact(
        self,
        assessment: dict[str, Any],
        patent_data: dict[str, Any],
    ) -> AnalysisArtifact:
        """
        Create a deep dive artifact for a single patent.
        
        Args:
            assessment: Patent assessment data
            patent_data: Full patent data from the active patent provider
            
        Returns:
            DeepDiveArtifact
        """
        # Extract applicants from nested structure
        applicants_data = _safe_get_nested(patent_data, "biblio.parties.applicants", [])
        applicants = []
        if isinstance(applicants_data, list):
            for app in applicants_data:
                if isinstance(app, dict):
                    # Try multiple fields where name might be
                    name = None
                    if "extracted_name" in app and isinstance(app["extracted_name"], dict):
                        name = app["extracted_name"].get("value")  # Changed from 'name' to 'value'
                    if not name:
                        name = app.get("name")
                    if not name:
                        name = app.get("full_name")
                    if name and isinstance(name, str):
                        applicants.append(name)
        
        # Extract inventors from nested structure
        inventors_data = _safe_get_nested(patent_data, "biblio.parties.inventors", [])
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
        
        # Get dates
        date_published = patent_data.get("date_published")
        legal_status = patent_data.get("legal_status", {})
        date_discontinued = legal_status.get("discontinued_date")
        
        # Extract abstract (can be array or string)
        abstract_data = patent_data.get("abstract", "No abstract available")
        if isinstance(abstract_data, list) and len(abstract_data) > 0:
            abstract = abstract_data[0].get("text", "No abstract available") if isinstance(abstract_data[0], dict) else str(abstract_data[0])
        else:
            abstract = str(abstract_data) if abstract_data else "No abstract available"
        
        artifact = AnalysisArtifact(
            record_id=assessment.get("record_id") or assessment.get("lens_id") or assessment.get("epo_id") or "UNKNOWN",
            lens_id=assessment.get("lens_id"),
            epo_id=assessment.get("epo_id"),
            provider_name=assessment.get("provider_name", "unknown"),
            provider_record_url=assessment.get("provider_record_url"),
            patent_number=assessment.get("doc_number", "UNKNOWN"),
            jurisdiction=assessment.get("jurisdiction", "UNKNOWN"),
            title=assessment.get("title", "Untitled"),
            status_summary=assessment.get("summary", ""),
            relevance_score=assessment.get("relevance_score", 0.0),
            intelligence_value=assessment.get("intelligence_value", "LOW"),
            classification_tags=assessment.get("classification_tags", []),
            abstract=abstract,
            rejection_reason=assessment.get("status_analysis", {}).get(
                "refusal_reason", "Unknown"
            ),
            applicants=applicants,
            inventors=inventors,
            date_published=date_published,
            date_discontinued=date_discontinued,
        )
        
        logger.info(f"🔬 Created deep dive artifact for {artifact.record_id}")
        return artifact


# Convenience functions

def generate_dashboard(
    assessments: list[dict[str, Any]],
    jurisdictions: list[str],
    mission_id: str | None = None,
) -> DashboardArtifact:
    """
    Quick function to generate a dashboard artifact.
    
    Args:
        assessments: Patent assessments
        jurisdictions: Jurisdictions searched
        mission_id: Optional mission ID
        
    Returns:
        DashboardArtifact
    """
    generator = ArtifactGenerator(mission_id)
    return generator.create_dashboard_artifact(assessments, jurisdictions)


def generate_review(
    assessments: list[dict[str, Any]],
    filter_level: str | None = None,
) -> ReviewArtifact:
    """
    Quick function to generate a review artifact.
    
    Args:
        assessments: Patent assessments
        filter_level: Optional priority filter
        
    Returns:
        ReviewArtifact
    """
    generator = ArtifactGenerator()
    return generator.create_review_artifact(assessments, filter_level)

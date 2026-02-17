"""
INPADOC Legal Status Decoder for Project Aether.
Implements forensic analysis of patent legal status codes.
Based on implementation plan Section 5.2 and 10.2.
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger("INPADOCDecoder")


class StatusSeverity(Enum):
    """Severity levels for patent status analysis."""
    HIGH = "HIGH"           # Substantive rejection - high intelligence value
    MEDIUM = "MEDIUM"       # Withdrawal or administrative - moderate value
    LOW = "LOW"             # Fee lapse or routine - low value
    UNKNOWN = "UNKNOWN"     # Unable to decode


@dataclass
class StatusAnalysis:
    """
    Result of analyzing a patent's legal status.
    """
    is_refused: bool
    is_withdrawn: bool
    is_lapsed: bool
    is_expired: bool
    is_inactive: bool
    is_active: bool
    is_pending: bool
    severity: StatusSeverity
    refusal_reason: str
    code_found: Optional[str]
    jurisdiction: str
    interpretation: str
    original_status: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_refused": self.is_refused,
            "is_withdrawn": self.is_withdrawn,
            "is_lapsed": self.is_lapsed,
            "is_expired": self.is_expired,
            "is_inactive": self.is_inactive,
            "is_active": self.is_active,
            "is_pending": self.is_pending,
            "severity": self.severity.value,
            "refusal_reason": self.refusal_reason,
            "code_found": self.code_found,
            "jurisdiction": self.jurisdiction,
            "interpretation": self.interpretation,
            "original_status": self.original_status,
        }


# INPADOC Event Code Database
# Based on WIPO ST.17 and implementation plan Table 1
INPADOC_CODES = {
    # === RUSSIA (RU) ===
    "RU": {
        "FC9A": {
            "description": "Refusal Decision by Examiner",
            "severity": StatusSeverity.HIGH,
            "interpretation": (
                "🚨 RED ALERT: Substantive examination refusal. "
                "Likely Article 1352 (Industrial Applicability). "
                "High probability of 'impossible' or 'anomalous' claims."
            ),
        },
        "FA9A": {
            "description": "Application Withdrawn by Applicant",
            "severity": StatusSeverity.MEDIUM,
            "interpretation": (
                "⚠️ Applicant withdrawal. Possible lack of funds, strategic "
                "concealment, or anticipation of rejection."
            ),
        },
        "MM4A": {
            "description": "Patent Lapsed Due to Non-Payment of Fees",
            "severity": StatusSeverity.LOW,
            "interpretation": "Administrative lapse. Low intelligence value.",
        },
        "FZ9A": {
            "description": "Application Deemed Withdrawn",
            "severity": StatusSeverity.MEDIUM,
            "interpretation": "Deemed withdrawn due to procedural failure.",
        },
    },
    
    # === EUROPEAN PATENT OFFICE (EP) ===
    "EP": {
        "R": {
            "description": "Refusal After Examination",
            "severity": StatusSeverity.HIGH,
            "interpretation": (
                "🚨 EPO substantive refusal. Patent failed examination. "
                "High intelligence value."
            ),
        },
        "QZ": {
            "description": "Application Withdrawn",
            "severity": StatusSeverity.MEDIUM,
            "interpretation": "Generic withdrawal. Moderate intelligence value.",
        },
        "STPP": {
            "description": "Refusal - Application Stopped",
            "severity": StatusSeverity.HIGH,
            "interpretation": "Prosecution stopped after refusal.",
        },
        "MM": {
            "description": "Lapsed (Fee Not Paid)",
            "severity": StatusSeverity.LOW,
            "interpretation": "Administrative lapse.",
        },
        "STAA": {
            "description": "Information on the Status of an EP Patent Application or Granted EP Patent",
            "severity": StatusSeverity.LOW,
            "interpretation": "Status update notification. International publication made.",
        },
        "PUAI": {
            "description": "Public Reference Made - EP Patent Entered European Phase",
            "severity": StatusSeverity.LOW,
            "interpretation": "Application entered European phase after public reference.",
        },
        "REG": {
            "description": "Patent Registration",
            "severity": StatusSeverity.LOW,
            "interpretation": "Patent has been registered and is now active.",
        },
        "GRNT": {
            "description": "Patent Granted",
            "severity": StatusSeverity.LOW,
            "interpretation": "Patent has been granted.",
        },
    },
    
    # === POLAND (PL) ===
    "PL": {
        "MM4A": {
            "description": "Lapsed Due to Non-Payment",
            "severity": StatusSeverity.LOW,
            "interpretation": "Administrative lapse.",
        },
        "ST05": {
            "description": "Patent Refused",
            "severity": StatusSeverity.HIGH,
            "interpretation": "Substantive refusal by Polish Patent Office.",
        },
    },
    
    # === ROMANIA (RO) ===
    "RO": {
        "MM4A": {
            "description": "Lapsed Due to Non-Payment",
            "severity": StatusSeverity.LOW,
            "interpretation": "Administrative lapse.",
        },
    },
    
    # === CZECHIA (CZ) ===
    "CZ": {
        "MM4A": {
            "description": "Lapsed Due to Non-Payment",
            "severity": StatusSeverity.LOW,
            "interpretation": "Administrative lapse.",
        },
    },
    
    # === NETHERLANDS (NL) ===
    "NL": {
        "MM": {
            "description": "Patent Lapsed",
            "severity": StatusSeverity.LOW,
            "interpretation": "Administrative lapse.",
        },
    },
    
    # === SPAIN (ES) ===
    "ES": {
        "FD2A": {
            "description": "Patent Lapsed",
            "severity": StatusSeverity.LOW,
            "interpretation": "Administrative lapse.",
        },
    },
    
    # === ITALY (IT) ===
    "IT": {
        "MM": {
            "description": "Patent Lapsed",
            "severity": StatusSeverity.LOW,
            "interpretation": "Administrative lapse.",
        },
    },
    
    # === SWEDEN (SE) ===
    "SE": {
        "MM": {
            "description": "Patent Lapsed",
            "severity": StatusSeverity.LOW,
            "interpretation": "Administrative lapse.",
        },
    },
    
    # === NORWAY (NO) ===
    "NO": {
        "MM": {
            "description": "Patent Lapsed",
            "severity": StatusSeverity.LOW,
            "interpretation": "Administrative lapse.",
        },
    },
    
    # === FINLAND (FI) ===
    "FI": {
        "MM": {
            "description": "Patent Lapsed",
            "severity": StatusSeverity.LOW,
            "interpretation": "Administrative lapse.",
        },
    },
}


def analyze_legal_status(patent_record: Dict) -> StatusAnalysis:
    """
    Decode INPADOC codes to determine if a patent was refused or just withdrawn.
    Critical for distinguishing failed science from bankrupt inventors.
    
    This is the core forensic function mentioned in implementation plan Section 10.2.
    
    Analyzes a chronologically ordered chain of legal events to determine the
    patent's current status and whether it experienced a substantive refusal.
    
    Args:
        patent_record: Patent data with:
                      - jurisdiction: str
                      - legal_status: dict with events array (sorted by date)
    
    Returns:
        StatusAnalysis object with detailed interpretation
    """
    jurisdiction = patent_record.get("jurisdiction", "UNKNOWN").upper()
    legal_status = patent_record.get("legal_status", {})
    events = legal_status.get("events", [])
    patent_status = legal_status.get("patent_status", "").upper()
    
    logger.info(f"Analyzing legal status for {jurisdiction} - Status: {patent_status}, Events: {len(events)}")
    
    # Initialize analysis result
    analysis = StatusAnalysis(
        is_refused=False,
        is_withdrawn=False,
        is_lapsed=False,
        is_expired=False,
        is_inactive=False,
        is_active=False,
        is_pending=False,
        severity=StatusSeverity.UNKNOWN,
        refusal_reason="Unknown",
        code_found=None,
        jurisdiction=jurisdiction,
        interpretation="No legal status events found.",
        original_status=None,
    )
    
    # First, check the patent_status field directly (this is the current status)
    if patent_status:
        analysis.original_status = patent_status
        if "REJECTED" in patent_status or "REFUSED" in patent_status:
            analysis.is_refused = True
            analysis.severity = StatusSeverity.HIGH
            analysis.refusal_reason = f"Patent Status: {patent_status}"
            analysis.interpretation = f"🚨 Patent marked as {patent_status}"
            logger.info(f"Patent refused based on status: {patent_status}")
        elif "WITHDRAWN" in patent_status:
            analysis.is_withdrawn = True
            analysis.severity = StatusSeverity.MEDIUM
            analysis.refusal_reason = f"Patent Status: {patent_status}"
            analysis.interpretation = f"⚠️ Patent marked as {patent_status}"
            logger.info(f"Patent withdrawn based on status: {patent_status}")
        elif "DISCONTINUED" in patent_status:
            analysis.is_withdrawn = True
            analysis.severity = StatusSeverity.MEDIUM
            analysis.refusal_reason = f"Patent Status: {patent_status}"
            analysis.interpretation = f"⚠️ Patent marked as {patent_status}"
            logger.info(f"Patent discontinued based on status: {patent_status}")
        elif "EXPIRED" in patent_status:
            analysis.is_expired = True
            analysis.severity = StatusSeverity.LOW
            analysis.refusal_reason = f"Patent Status: {patent_status}"
            analysis.interpretation = f"Patent marked as {patent_status}"
            logger.info(f"Patent expired based on status: {patent_status}")
        elif "LAPSED" in patent_status:
            analysis.is_lapsed = True
            analysis.severity = StatusSeverity.LOW
            analysis.refusal_reason = f"Patent Status: {patent_status}"
            analysis.interpretation = f"Patent marked as {patent_status}"
            logger.info(f"Patent lapsed based on status: {patent_status}")
        elif "INACTIVE" in patent_status:
            analysis.is_inactive = True
            analysis.severity = StatusSeverity.LOW
            analysis.refusal_reason = f"Patent Status: {patent_status}"
            analysis.interpretation = f"Patent marked as {patent_status}"
            logger.info(f"Patent inactive based on status: {patent_status}")
        elif "ACTIVE" in patent_status:
            analysis.is_active = True
            analysis.severity = StatusSeverity.LOW
            analysis.refusal_reason = f"Patent Status: {patent_status}"
            analysis.interpretation = f"Patent marked as {patent_status}"
            logger.info(f"Patent active based on status: {patent_status}")
        elif "PENDING" in patent_status:
            analysis.is_pending = True
            analysis.severity = StatusSeverity.LOW
            analysis.refusal_reason = f"Patent Status: {patent_status}"
            analysis.interpretation = f"Patent marked as {patent_status}"
            logger.info(f"Patent pending based on status: {patent_status}")
    
    if not events:
        logger.warning(f"No legal events found for patent in {jurisdiction}")
        return analysis
    
    # Get jurisdiction-specific code database
    jurisdiction_codes = INPADOC_CODES.get(jurisdiction, {})
    
    # Scan for significant events (refusals) first - these take precedence
    # Events are sorted chronologically, so we can scan them
    for event in events:
        event_code = event.get("event_code", "").upper()
        event_date = event.get("date", "")
        event_description = event.get("description", "")
        
        logger.debug(f"Analyzing event: {event_code} (date: {event_date}) - {event_description}")
        
        # Check if we have this code in our database
        if event_code in jurisdiction_codes:
            code_info = jurisdiction_codes[event_code]
            
            # For refusals, stop immediately - this is a high-priority finding
            if code_info["severity"] == StatusSeverity.HIGH:
                analysis.code_found = event_code
                analysis.refusal_reason = code_info["description"]
                analysis.severity = code_info["severity"]
                analysis.interpretation = code_info["interpretation"]
                analysis.is_refused = True
                logger.info(
                    f"🚨 HIGH PRIORITY: {jurisdiction} patent with code {event_code} at {event_date} "
                    f"- {code_info['description']}"
                )
                return analysis
    
    # Check for common refusal patterns across any event code
    for event in events:
        event_code = event.get("event_code", "").upper()
        event_description = event.get("description", "").upper()
        
        if "REFUS" in event_code or "REFUS" in event_description:
            analysis.is_refused = True
            analysis.severity = StatusSeverity.HIGH
            analysis.code_found = event_code
            analysis.refusal_reason = event.get("description") or "Refusal (unknown code)"
            analysis.interpretation = f"⚠️ Refusal detected: {event_code}"
            logger.info(f"🚨 Refusal found via code/description: {event_code}")
            return analysis
    
    # If no refusal found, categorize based on most recent event
    # (Events are sorted chronologically, so last is most recent)
    if events:
        latest_event = events[-1]
        event_code = latest_event.get("event_code", "").upper()
        event_date = latest_event.get("date", "")
        event_description = latest_event.get("description", "").upper()
        
        logger.debug(f"Most recent event: {event_code} ({event_date})")
        
        # Check if we have this code in our database
        if event_code in jurisdiction_codes:
            code_info = jurisdiction_codes[event_code]
            analysis.code_found = event_code
            analysis.refusal_reason = code_info["description"]
            analysis.severity = code_info["severity"]
            analysis.interpretation = code_info["interpretation"]
            
            # Set flags based on code type
            if "refusal" in code_info["description"].lower() or "refused" in code_info["description"].lower():
                analysis.is_refused = True
            elif "withdrawn" in code_info["description"].lower():
                analysis.is_withdrawn = True
            elif "lapsed" in code_info["description"].lower():
                analysis.is_lapsed = True
            elif "granted" in code_info["description"].lower():
                analysis.is_active = True
        
        # Check for common patterns even if specific code not in database
        elif "WITHDRAW" in event_description:
            analysis.is_withdrawn = True
            analysis.severity = StatusSeverity.MEDIUM
            analysis.code_found = event_code
            analysis.refusal_reason = latest_event.get("description", "")
            analysis.interpretation = "Withdrawn by applicant."
        elif "LAPSED" in event_description or "LAPSE" in event_description:
            analysis.is_lapsed = True
            analysis.severity = StatusSeverity.LOW
            analysis.code_found = event_code
            analysis.refusal_reason = latest_event.get("description", "")
            analysis.interpretation = "Patent lapsed - likely due to non-payment."
        elif "EXPIRED" in event_description:
            analysis.is_expired = True
            analysis.severity = StatusSeverity.LOW
            analysis.code_found = event_code
            analysis.refusal_reason = latest_event.get("description", "")
            analysis.interpretation = "Patent expired after normal term."
        elif "GRANTED" in event_description or "GRNT" in event_code:
            analysis.is_active = True
            analysis.severity = StatusSeverity.LOW
            analysis.code_found = event_code
            analysis.refusal_reason = latest_event.get("description", "")
            analysis.interpretation = "✓ Patent granted and currently active."
        else:
            # For status events like STAA, PUAI, treat as pending/active
            analysis.is_pending = True
            analysis.severity = StatusSeverity.LOW
            analysis.code_found = event_code
            analysis.refusal_reason = latest_event.get("description", "")
            analysis.interpretation = f"Patent under prosecution or pending: {event_code}"
    
    return analysis


def is_high_value_rejection(patent_record: Dict) -> bool:
    """
    Quick check if a patent is a high-value rejection.
    Returns True for substantive rejections (FC9A in Russia, R in EPO, etc.)
    
    Args:
        patent_record: Patent data from Lens.org
        
    Returns:
        True if this is a high-value rejection
    """
    analysis = analyze_legal_status(patent_record)
    return analysis.severity == StatusSeverity.HIGH and analysis.is_refused


def batch_analyze_patents(patent_records: List[Dict]) -> List[StatusAnalysis]:
    """
    Analyze multiple patents in batch.
    
    Args:
        patent_records: List of patent records from Lens.org
        
    Returns:
        List of StatusAnalysis objects
    """
    results = []
    
    for record in patent_records:
        try:
            analysis = analyze_legal_status(record)
            results.append(analysis)
        except Exception as e:
            logger.error(f"Failed to analyze patent: {e}")
            # Add a default "unknown" analysis
            results.append(
                StatusAnalysis(
                    is_refused=False,
                    is_withdrawn=False,
                    is_lapsed=False,
                    is_expired=False,
                    is_inactive=False,
                    is_active=False,
                    is_pending=False,
                    severity=StatusSeverity.UNKNOWN,
                    refusal_reason=f"Analysis failed: {str(e)}",
                    code_found=None,
                    jurisdiction="UNKNOWN",
                    interpretation="Error during analysis",
                )
            )
    
    return results


def get_rejection_statistics(analyses: List[StatusAnalysis]) -> Dict[str, int]:
    """
    Generate statistics from a batch of status analyses.
    
    Args:
        analyses: List of StatusAnalysis objects
        
    Returns:
        Dictionary with counts by severity and type
    """
    stats = {
        "total": len(analyses),
        "high_priority": 0,
        "medium_priority": 0,
        "low_priority": 0,
        "refused": 0,
        "withdrawn": 0,
        "lapsed": 0,
        "unknown": 0,
    }
    
    for analysis in analyses:
        if analysis.severity == StatusSeverity.HIGH:
            stats["high_priority"] += 1
        elif analysis.severity == StatusSeverity.MEDIUM:
            stats["medium_priority"] += 1
        elif analysis.severity == StatusSeverity.LOW:
            stats["low_priority"] += 1
        else:
            stats["unknown"] += 1
        
        if analysis.is_refused:
            stats["refused"] += 1
        if analysis.is_withdrawn:
            stats["withdrawn"] += 1
        if analysis.is_lapsed:
            stats["lapsed"] += 1
    
    return stats

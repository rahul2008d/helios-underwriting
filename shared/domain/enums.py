"""Enumerations used throughout the insurance domain."""

from enum import StrEnum


class SubmissionStatus(StrEnum):
    """Lifecycle states of a submission as it moves through underwriting."""

    RECEIVED = "received"
    """Submission has been ingested but not yet processed."""

    PARSING = "parsing"
    """Document parser is extracting structured data."""

    TRIAGED = "triaged"
    """Triage agent has classified the submission."""

    ASSESSED = "assessed"
    """Risk assessment is complete."""

    QUOTED = "quoted"
    """A quote has been generated."""

    BOUND = "bound"
    """Quote accepted and policy bound."""

    DECLINED = "declined"
    """Submission has been declined and will not be quoted."""

    EXPIRED = "expired"
    """Submission expired without being bound."""


class TriageDecision(StrEnum):
    """Possible decisions from the triage agent."""

    ACCEPT = "accept"
    """Falls within appetite, proceed to full assessment."""

    REFER = "refer"
    """Edge case requiring human underwriter review."""

    DECLINE = "decline"
    """Outside appetite, do not proceed."""


class RiskBand(StrEnum):
    """Overall risk classification after assessment."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class VehicleType(StrEnum):
    """Categories of commercial vehicles in a fleet."""

    VAN = "van"
    """Light commercial vehicle, under 3.5t."""

    LORRY = "lorry"
    """Rigid HGV, 3.5t to 18t."""

    ARTICULATED = "articulated"
    """Articulated HGV, over 18t."""

    REFRIGERATED = "refrigerated"
    """Temperature-controlled goods vehicle."""

    HAZARDOUS = "hazardous"
    """Vehicle carrying dangerous goods."""

    SPECIALIST = "specialist"
    """Specialist commercial vehicle, e.g. recovery, plant."""


class CoverageType(StrEnum):
    """Types of insurance coverage offered."""

    THIRD_PARTY_ONLY = "third_party_only"
    THIRD_PARTY_FIRE_THEFT = "third_party_fire_theft"
    COMPREHENSIVE = "comprehensive"


class PolicyStatus(StrEnum):
    """Lifecycle states of a bound policy."""

    ACTIVE = "active"
    """Policy is currently in force."""

    LAPSED = "lapsed"
    """Policy expired without renewal."""

    CANCELLED = "cancelled"
    """Policy was cancelled mid-term."""

    RENEWED = "renewed"
    """Policy was renewed into a new term."""


class Currency(StrEnum):
    """Supported currency codes for premiums."""

    GBP = "GBP"
    USD = "USD"
    EUR = "EUR"

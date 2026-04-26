"""Repositories package for the risk service."""

from services.risk.repositories.assessment_repository import AssessmentRepository
from services.risk.repositories.triage_repository import TriageRepository

__all__ = ["AssessmentRepository", "TriageRepository"]

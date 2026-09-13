"""
Adaptive Therapy Difficulty Engine Models
Represents clinician-controlled difficulty configuration, adaptation recommendations,
and audit trail for VR eye-rehabilitation therapy sessions.
Strictly non-diagnostic and rule-based decision-support only.
"""

from datetime import datetime
from typing import Any, Dict, Optional

try:
    from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Text, ForeignKey
    from sqlalchemy.orm import declarative_base, relationship
    Base = declarative_base()
except ImportError:
    Base = object
    Column = String = Integer = Float = Boolean = DateTime = JSON = Text = ForeignKey = relationship = lambda *args, **kwargs: None


class AdaptiveTherapyConfig(Base):
    __tablename__ = "adaptive_therapy_configs"

    id = Column(String(64), primary_key=True, index=True)
    patient_id = Column(String(64), nullable=False, index=True)
    therapy_assignment_id = Column(String(64), nullable=True, index=True)
    exercise_id = Column(String(64), nullable=False, index=True)

    enabled = Column(Boolean, default=True, nullable=False)
    # Modes: 'disabled', 'manual_only', 'controlled_automatic'
    adaptive_mode = Column(String(32), default="controlled_automatic", nullable=False)

    minimum_difficulty = Column(Integer, default=1, nullable=False)
    maximum_difficulty = Column(Integer, default=5, nullable=False)
    starting_difficulty = Column(Integer, default=2, nullable=False)
    current_difficulty = Column(Integer, default=2, nullable=False)

    progression_threshold = Column(Float, default=85.0, nullable=False)
    regression_threshold = Column(Float, default=50.0, nullable=False)
    step_size = Column(Integer, default=1, nullable=False)
    minimum_sessions_before_adaptation = Column(Integer, default=2, nullable=False)
    max_daily_difficulty_increase = Column(Integer, default=1, nullable=False)
    clinician_approval_required = Column(Boolean, default=True, nullable=False)

    created_by = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "therapy_assignment_id": self.therapy_assignment_id,
            "exercise_id": self.exercise_id,
            "enabled": self.enabled,
            "adaptive_mode": self.adaptive_mode,
            "minimum_difficulty": self.minimum_difficulty,
            "maximum_difficulty": self.maximum_difficulty,
            "starting_difficulty": self.starting_difficulty,
            "current_difficulty": self.current_difficulty,
            "progression_threshold": self.progression_threshold,
            "regression_threshold": self.regression_threshold,
            "step_size": self.step_size,
            "minimum_sessions_before_adaptation": self.minimum_sessions_before_adaptation,
            "max_daily_difficulty_increase": self.max_daily_difficulty_increase,
            "clinician_approval_required": self.clinician_approval_required,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at),
            "notice": "Controlled rule-based difficulty adaptation. Does not diagnose or determine recovery. Follow clinician guidance."
        }


class TherapyAdaptationRecommendation(Base):
    __tablename__ = "therapy_adaptation_recommendations"

    id = Column(String(64), primary_key=True, index=True)
    patient_id = Column(String(64), nullable=False, index=True)
    therapy_assignment_id = Column(String(64), nullable=True, index=True)
    exercise_id = Column(String(64), nullable=False, index=True)
    source_session_id = Column(String(64), nullable=True, index=True)

    current_difficulty = Column(Integer, nullable=False)
    recommended_difficulty = Column(Integer, nullable=False)
    # Direction: 'progression', 'regression', 'maintain', 'pause_discomfort'
    direction = Column(String(32), default="maintain", nullable=False)
    reason = Column(Text, nullable=False)
    supporting_metrics = Column(JSON, default=dict)

    # Reliability & Data quality indicators
    confidence = Column(String(32), default="high")
    data_quality_note = Column(Text, default="Based on verified session telemetry.")
    is_simulated_data = Column(Boolean, default=False)

    # States: 'pending', 'approved', 'rejected', 'applied', 'overridden', 'cancelled', 'not_recommended'
    status = Column(String(32), default="pending", nullable=False)

    reviewed_by = Column(String(128), nullable=True)
    clinician_note = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "therapy_assignment_id": self.therapy_assignment_id,
            "exercise_id": self.exercise_id,
            "source_session_id": self.source_session_id,
            "current_difficulty": self.current_difficulty,
            "recommended_difficulty": self.recommended_difficulty,
            "direction": self.direction,
            "reason": self.reason,
            "supporting_metrics": self.supporting_metrics,
            "confidence": self.confidence,
            "data_quality_note": self.data_quality_note,
            "is_simulated_data": self.is_simulated_data,
            "status": self.status,
            "reviewed_by": self.reviewed_by,
            "clinician_note": self.clinician_note,
            "reviewed_at": self.reviewed_at.isoformat() if isinstance(self.reviewed_at, datetime) else str(self.reviewed_at) if self.reviewed_at else None,
            "applied_at": self.applied_at.isoformat() if isinstance(self.applied_at, datetime) else str(self.applied_at) if self.applied_at else None,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "notice": "Suggested difficulty adjustment based on performance rules. Requires clinician review before application when configured."
        }


class TherapyAdaptationAudit(Base):
    __tablename__ = "therapy_adaptation_audits"

    id = Column(String(64), primary_key=True, index=True)
    patient_id = Column(String(64), nullable=False, index=True)
    exercise_id = Column(String(64), nullable=False, index=True)

    previous_difficulty = Column(Integer, nullable=False)
    new_difficulty = Column(Integer, nullable=False)

    # Change type: 'automatic', 'clinician_approved', 'clinician_override', 'reset'
    change_type = Column(String(32), nullable=False)
    # Trigger: 'session_completion', 'clinician_action', 'initial_setup'
    trigger = Column(String(32), nullable=False)
    source_recommendation_id = Column(String(64), nullable=True)

    applied_by = Column(String(128), default="system")
    applied_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "exercise_id": self.exercise_id,
            "previous_difficulty": self.previous_difficulty,
            "new_difficulty": self.new_difficulty,
            "change_type": self.change_type,
            "trigger": self.trigger,
            "source_recommendation_id": self.source_recommendation_id,
            "applied_by": self.applied_by,
            "applied_at": self.applied_at.isoformat() if isinstance(self.applied_at, datetime) else str(self.applied_at),
            "notes": self.notes
        }

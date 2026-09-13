"""
Therapy Session and Result Models
Represents VR/visual therapy rehabilitation sessions and recorded performance metrics.
Strictly non-diagnostic and prototype decision-support only.
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


class TherapySession(Base):
    __tablename__ = "therapy_sessions"

    id = Column(String(64), primary_key=True, index=True)
    patient_id = Column(String(64), nullable=False, index=True)
    recommendation_id = Column(String(64), nullable=True, index=True)
    assigned_by = Column(String(128), nullable=True)

    # Valid exercise types: 'fixation_target', 'horizontal_moving_target', 'gaze_target_selection'
    exercise_type = Column(String(64), nullable=False)

    # State machine: 'assigned', 'ready', 'in_progress', 'paused', 'completed', 'stopped', 'abandoned', 'error'
    session_status = Column(String(32), default="ready", nullable=False)

    planned_duration_seconds = Column(Integer, default=300, nullable=False)
    actual_duration_seconds = Column(Integer, default=0, nullable=False)
    difficulty = Column(String(32), default="beginner", nullable=False)

    started_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    stop_reason = Column(String(256), nullable=True)

    data_quality_status = Column(String(64), default="Demo/Simulated Tracking Data")
    is_simulated_data = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "recommendation_id": self.recommendation_id,
            "assigned_by": self.assigned_by,
            "exercise_type": self.exercise_type,
            "session_status": self.session_status,
            "planned_duration_seconds": self.planned_duration_seconds,
            "actual_duration_seconds": self.actual_duration_seconds,
            "difficulty": self.difficulty,
            "started_at": self.started_at.isoformat() if isinstance(self.started_at, datetime) else str(self.started_at) if self.started_at else None,
            "paused_at": self.paused_at.isoformat() if isinstance(self.paused_at, datetime) else str(self.paused_at) if self.paused_at else None,
            "completed_at": self.completed_at.isoformat() if isinstance(self.completed_at, datetime) else str(self.completed_at) if self.completed_at else None,
            "stopped_at": self.stopped_at.isoformat() if isinstance(self.stopped_at, datetime) else str(self.stopped_at) if self.stopped_at else None,
            "stop_reason": self.stop_reason,
            "data_quality_status": self.data_quality_status,
            "is_simulated_data": self.is_simulated_data,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at),
            "notice": "Prototype rehabilitation session. Follow clinician instructions. Stop if discomfort occurs. Recorded results are not a diagnosis."
        }


class TherapySessionResult(Base):
    __tablename__ = "therapy_session_results"

    id = Column(String(64), primary_key=True, index=True)
    therapy_session_id = Column(String(64), nullable=False, index=True)
    patient_id = Column(String(64), nullable=False, index=True)
    exercise_type = Column(String(64), nullable=False)

    score = Column(Float, default=0.0)
    accuracy = Column(Float, default=0.0)
    error_value = Column(Float, nullable=True)
    reaction_time = Column(Float, nullable=True)
    completion_percentage = Column(Float, default=0.0)
    valid_sample_count = Column(Integer, default=0)
    tracking_confidence = Column(Float, default=0.9)
    target_loss_events = Column(Integer, default=0)
    pause_count = Column(Integer, default=0)

    metrics_json = Column(JSON, default=dict)
    data_quality_status = Column(String(64), default="Demo/Simulated Tracking Data")
    is_simulated_data = Column(Boolean, default=True)
    clinician_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "therapy_session_id": self.therapy_session_id,
            "patient_id": self.patient_id,
            "exercise_type": self.exercise_type,
            "score": self.score,
            "accuracy": self.accuracy,
            "error_value": self.error_value,
            "reaction_time": self.reaction_time,
            "completion_percentage": self.completion_percentage,
            "valid_sample_count": self.valid_sample_count,
            "tracking_confidence": self.tracking_confidence,
            "target_loss_events": self.target_loss_events,
            "pause_count": self.pause_count,
            "metrics_json": self.metrics_json,
            "data_quality_status": self.data_quality_status,
            "is_simulated_data": self.is_simulated_data,
            "clinician_notes": self.clinician_notes,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "notice": "Prototype rehabilitation session. Follow clinician instructions. Stop if discomfort occurs. Recorded results are not a diagnosis."
        }

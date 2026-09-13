"""
Therapy Recommendation Model
Represents AI-assisted clinical decision-support exercise recommendations.
Strictly requires clinician review prior to any therapy scheduling.
Never automatically assigns or starts therapy.
"""

from datetime import datetime
from typing import Any, Dict, Optional

try:
    from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Text, ForeignKey
    from sqlalchemy.orm import declarative_base, relationship
    Base = declarative_base()
except ImportError:
    # Graceful fallback if running in lightweight environment without SQLAlchemy core
    Base = object
    Column = String = Integer = Boolean = DateTime = JSON = Text = ForeignKey = relationship = lambda *args, **kwargs: None


class TherapyRecommendation(Base):
    __tablename__ = "therapy_recommendations"

    id = Column(String(64), primary_key=True, index=True)
    patient_id = Column(String(64), nullable=False, index=True)
    eye_test_session_id = Column(String(64), nullable=False, index=True)
    ai_analysis_id = Column(String(64), nullable=False, index=True)

    # Statuses: 'generated', 'pending_review', 'approved', 'edited', 'rejected', 'archived'
    recommendation_status = Column(String(32), default="pending_review", nullable=False)

    # Categories:
    # - 'Fixation Exercise'
    # - 'Smooth Pursuit Exercise'
    # - 'Saccade Exercise'
    # - 'Gaze Accuracy Exercise'
    # - 'General Visual Attention Exercise'
    # - 'Repeat Assessment / Calibration Review'
    exercise_category = Column(String(64), nullable=False)
    reason = Column(Text, nullable=False)
    supporting_metrics_json = Column(JSON, default=list)

    suggested_difficulty = Column(String(32), default="beginner")
    suggested_duration_min = Column(Integer, default=5)
    suggested_duration_max = Column(Integer, default=10)

    # Priority: 'low', 'moderate', 'high', 'review_required'
    priority = Column(String(32), default="moderate")
    confidence = Column(String(32), default="moderate")
    data_quality_note = Column(Text, default="Based on available session data.")
    is_simulated_data = Column(Boolean, default=False)

    # Clinician review status: 'pending', 'approved', 'edited', 'rejected'
    # MUST always begin as 'pending'
    clinician_review_status = Column(String(32), default="pending", nullable=False)
    clinician_notes = Column(Text, nullable=True)
    original_recommendation_json = Column(JSON, nullable=True)

    created_by = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "eye_test_session_id": self.eye_test_session_id,
            "ai_analysis_id": self.ai_analysis_id,
            "recommendation_status": self.recommendation_status,
            "exercise_category": self.exercise_category,
            "reason": self.reason,
            "supporting_metrics_json": self.supporting_metrics_json,
            "suggested_difficulty": self.suggested_difficulty,
            "suggested_duration_min": self.suggested_duration_min,
            "suggested_duration_max": self.suggested_duration_max,
            "priority": self.priority,
            "confidence": self.confidence,
            "data_quality_note": self.data_quality_note,
            "is_simulated_data": self.is_simulated_data,
            "clinician_review_status": self.clinician_review_status,
            "clinician_notes": self.clinician_notes,
            "original_recommendation_json": self.original_recommendation_json,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at),
            "disclaimer": "AI-assisted recommendation. Requires clinician review. Not a diagnosis or automatic prescription."
        }

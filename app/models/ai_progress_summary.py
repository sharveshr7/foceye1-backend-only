"""
AI Progress Summary Database Model
Represents clinician-initiated, non-diagnostic longitudinal analysis summaries.
Adheres strictly to clinical safety guardrails: no automatic treatment decisions,
no cure or disease recovery claims, and mandatory clinician review.
"""

from datetime import datetime
from typing import Any, Dict, Optional

try:
    from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Text
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()
except ImportError:
    Base = object
    Column = String = Integer = Boolean = DateTime = JSON = Text = lambda *args, **kwargs: None


class AIProgressSummary(Base):
    __tablename__ = "ai_progress_summaries"

    id = Column(String(64), primary_key=True, index=True)
    patient_id = Column(String(64), nullable=False, index=True)
    source_session_ids_json = Column(JSON, default=list)

    # Status: 'completed', 'pending', 'failed'
    summary_status = Column(String(32), default="completed", nullable=False)
    model_name = Column(String(64), default="gemini-2.5-flash", nullable=False)

    input_summary_json = Column(JSON, default=dict)
    output_json = Column(JSON, default=dict)

    # Data provenance and quality
    data_quality_status = Column(String(64), default="Valid Data")
    is_simulated_data = Column(Boolean, default=False)

    # Clinician review status: 'pending', 'reviewed', 'flagged', 'dismissed'
    clinician_review_status = Column(String(32), default="pending", nullable=False)
    clinician_notes = Column(Text, nullable=True)

    created_by = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

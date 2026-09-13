from fastapi import APIRouter, Depends, HTTPException, Response, status
from app.core.auth import UserProfile, get_current_user
from app.core.supabase import supabase
from app.schemas.report_schemas import ReportRequest
from app.services.ai_analyzer import AIAnalyzerService
from app.services.pdf_generator import PDFReportGenerator

router = APIRouter(prefix="/reports", tags=["Clinical PDF Reports"])


@router.post("/pdf", responses={200: {"content": {"application/pdf": {}}}})
async def generate_pdf_report(
    req: ReportRequest,
    user: UserProfile = Depends(get_current_user)
):
    # Fetch patient
    patient_res = supabase.table("patients").select("*").eq("id", req.patient_id).execute()
    if not patient_res.data or len(patient_res.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient record not found"
        )
    patient = patient_res.data[0]

    # Fetch latest session for actual telemetry metrics
    sessions_res = supabase.table("therapy_sessions").select("*").eq("patient_id", req.patient_id).execute()
    latest_session = sessions_res.data[-1] if sessions_res.data else {}

    fixation_val = float(latest_session.get("fixation_score", 88.5))
    saccadic_val = float(latest_session.get("saccadic_score", 90.0))
    # Approximate latency from saccadic score if latency not directly logged
    saccadic_latency = round(max(170.0, 360.0 - saccadic_val * 1.5), 1)
    bcea_val = float(latest_session.get("bcea_68") or patient.get("bcea_score", 1.0))
    adherence_val = float(patient.get("adherence", 95))

    # Generate AI synthesis with actual measured biomarkers
    ai_data = await AIAnalyzerService.analyze_patient_metrics(
        condition=patient.get("condition", "Amblyopia"),
        age=patient.get("age", 10),
        bcea_score=bcea_val,
        fixation_stability=fixation_val,
        saccadic_latency_ms=saccadic_latency,
        adherence_rate=adherence_val
    )

    pdf_bytes = PDFReportGenerator.generate_patient_report(
        patient_data=patient,
        ai_data=ai_data,
        therapist_name=req.therapist_signature or user.full_name,
        session_data=latest_session
    )

    filename = f"FOCEYE_Clinical_Report_{patient.get('id', 'patient')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

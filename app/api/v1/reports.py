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

    # Generate AI synthesis
    ai_data = await AIAnalyzerService.analyze_patient_metrics(
        condition=patient.get("condition", "Amblyopia"),
        age=patient.get("age", 10),
        bcea_score=patient.get("bcea_score", 1.2),
        fixation_stability=88.5,
        saccadic_latency_ms=210.0,
        adherence_rate=patient.get("adherence", 95)
    )

    pdf_bytes = PDFReportGenerator.generate_patient_report(
        patient_data=patient,
        ai_data=ai_data,
        therapist_name=req.therapist_signature or user.full_name
    )

    filename = f"FOCEYE_Clinical_Report_{patient.get('id', 'patient')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

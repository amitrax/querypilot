from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User, Analysis, Report
from app.schemas.report import ReportCreate, ReportOut
from app.schemas.analytics import AnalysisResultData
from app.api.deps import get_current_user
from app.storage.service import storage_service
from app.analytics.exporter import export_analysis_to_csv, generate_text_summary_report

router = APIRouter()


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    req: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generates an exportable CSV or text report for a completed analysis."""
    analysis = db.query(Analysis).filter(Analysis.id == req.analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if analysis.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized.")
    if not analysis.result:
        raise HTTPException(status_code=400, detail="Analysis has no computed results yet.")

    res_data = AnalysisResultData.model_validate(analysis.result.result_json)
    report_format = req.format.lower()

    if report_format == "csv":
        content = export_analysis_to_csv(res_data.columns, res_data.rows)
        filename = f"report_{analysis.id[:8]}.csv"
    else:
        content = generate_text_summary_report(
            question=analysis.question,
            operation_summary=str(analysis.analysis_plan_json.get("operation") if analysis.analysis_plan_json else "analysis"),
            explanation=analysis.result.explanation or "",
            columns=res_data.columns,
            rows=res_data.rows,
            execution_time_ms=res_data.execution_time_ms
        )
        filename = f"report_{analysis.id[:8]}.txt"

    storage_key, _ = storage_service.save_report_content(filename, content)

    report = Report(
        user_id=current_user.id,
        analysis_id=analysis.id,
        storage_key=storage_key,
        format=report_format,
        status="completed"
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return report


@router.get("", response_model=List[ReportOut])
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all generated reports for the current user."""
    return (
        db.query(Report)
        .filter(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .all()
    )


@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Securely downloads a generated report with strict ownership check."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to download this report.")

    file_path = storage_service.get_file_path(report.storage_key, folder="reports")
    media_type = "text/csv" if report.format == "csv" else "text/plain"
    
    return FileResponse(
        path=str(file_path),
        filename=f"querypilot_report_{report.id[:8]}.{report.format}",
        media_type=media_type
    )

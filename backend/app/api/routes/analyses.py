from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User, Dataset, Analysis, AnalysisResult
from app.schemas.analytics import AnalysisCreateRequest, AnalysisResponse, AnalysisResultData, AnalysisPlan
from app.api.deps import get_current_user
from app.storage.service import storage_service
from app.analytics.profiler import detect_encoding_and_read
from app.analytics.engine import analysis_engine, AnalysisEngineError
from app.ai.provider import get_ai_provider

router = APIRouter()


@router.post("", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
def create_analysis(
    request: AnalysisCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits a natural language data analysis question:
    1. Validates dataset ownership
    2. Formulates a structured AnalysisPlan (via AI provider or fallback)
    3. Executes deterministically using pure pandas operations
    4. Generates an evidence-backed explanation
    5. Persists the analysis and result
    """
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if dataset.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset.")

    # Load dataset file
    file_path = storage_service.get_file_path(dataset.storage_key)
    df = detect_encoding_and_read(str(file_path))

    ai_provider = get_ai_provider()

    # Step 1: Formulate Analysis Plan
    if request.plan_override:
        plan = request.plan_override
    else:
        sample_records = df.head(5).to_dict(orient="records")
        try:
            plan = ai_provider.generate_plan(
                question=request.question,
                schema_info=dataset.schema_json or [],
                sample_data=sample_records
            )
        except AnalysisEngineError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Step 2: Create initial analysis record
    analysis = Analysis(
        user_id=current_user.id,
        dataset_id=dataset.id,
        question=request.question,
        status="pending",
        analysis_plan_json=plan.model_dump(),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Step 3: Execute deterministically with AnalysisEngine
    try:
        result_data = analysis_engine.execute(df, plan)
        explanation = ai_provider.explain_results(request.question, plan, result_data)

        # Update analysis status
        analysis.status = "completed"
        analysis.error_message = None

        # Persist result
        analysis_result = AnalysisResult(
            analysis_id=analysis.id,
            result_json=result_data.model_dump(),
            explanation=explanation,
        )
        db.add(analysis_result)
        db.commit()
        db.refresh(analysis)

        return AnalysisResponse(
            id=analysis.id,
            dataset_id=analysis.dataset_id,
            question=analysis.question,
            status=analysis.status,
            analysis_plan=plan,
            result=result_data,
            explanation=explanation,
            created_at=analysis.created_at.isoformat(),
        )

    except AnalysisEngineError as e:
        analysis.status = "failed"
        analysis.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=400, detail=f"Analysis execution error: {str(e)}")
    except Exception as e:
        analysis.status = "failed"
        analysis.error_message = f"Unexpected execution error: {str(e)}"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("", response_model=List[AnalysisResponse])
def list_analyses(
    dataset_id: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists saved analyses for the authenticated user."""
    query = db.query(Analysis).filter(Analysis.user_id == current_user.id)
    if dataset_id:
        ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not ds:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        if ds.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this dataset.")
        query = query.filter(Analysis.dataset_id == dataset_id)

    analyses = query.order_by(Analysis.created_at.desc()).all()

    out = []
    for a in analyses:
        res_data = None
        exp = None
        if a.result:
            try:
                res_data = AnalysisResultData.model_validate(a.result.result_json)
                exp = a.result.explanation
            except Exception:
                pass

        plan = AnalysisPlan.model_validate(a.analysis_plan_json) if a.analysis_plan_json else None

        out.append(
            AnalysisResponse(
                id=a.id,
                dataset_id=a.dataset_id,
                question=a.question,
                status=a.status,
                analysis_plan=plan,
                error_message=a.error_message,
                result=res_data,
                explanation=exp,
                created_at=a.created_at.isoformat(),
            )
        )
    return out


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves an analysis by ID with ownership verification."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if analysis.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this analysis.")

    res_data = None
    exp = None
    if analysis.result:
        res_data = AnalysisResultData.model_validate(analysis.result.result_json)
        exp = analysis.result.explanation

    plan = AnalysisPlan.model_validate(analysis.analysis_plan_json) if analysis.analysis_plan_json else None

    return AnalysisResponse(
        id=analysis.id,
        dataset_id=analysis.dataset_id,
        question=analysis.question,
        status=analysis.status,
        analysis_plan=plan,
        error_message=analysis.error_message,
        result=res_data,
        explanation=exp,
        created_at=analysis.created_at.isoformat(),
    )


@router.delete("/{analysis_id}", status_code=status.HTTP_200_OK)
def delete_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deletes a saved analysis."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if analysis.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this analysis.")

    db.delete(analysis)
    db.commit()
    return {"message": "Analysis deleted."}

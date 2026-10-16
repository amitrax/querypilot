import io
import pandas as pd
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User, Dataset
from app.schemas.dataset import DatasetSummary, DatasetDetail, DatasetPreview, DatasetProfile
from app.api.deps import get_current_user
from app.storage.service import storage_service
from app.analytics.profiler import detect_encoding_and_read, normalize_column_names, profile_dataframe

router = APIRouter()


@router.get("", response_model=List[DatasetSummary])
def list_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all datasets owned by the authenticated user."""
    datasets = (
        db.query(Dataset)
        .filter(Dataset.user_id == current_user.id)
        .order_by(Dataset.created_at.desc())
        .all()
    )
    return datasets


@router.post("/upload", response_model=DatasetDetail, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads and processes a CSV file:
    - Validates file format and structure
    - Normalizes column names
    - Calculates row/column counts and profiling metrics
    - Persists dataset record
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected.")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files (.csv) are currently supported."
        )

    # Save file securely to storage
    storage_key, file_path, file_size = storage_service.save_upload(file.file, file.filename)

    # Read and validate dataframe
    try:
        df = detect_encoding_and_read(file_path)
    except Exception as e:
        storage_service.delete_file(storage_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse CSV file: {str(e)}"
        )

    if df.empty and len(df.columns) == 0:
        storage_service.delete_file(storage_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded CSV file is empty."
        )

    # Protect against column or row explosion DoS
    if len(df.columns) > 500:
        storage_service.delete_file(storage_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset exceeds maximum allowed column count of 500."
        )

    if len(df) > 1_000_000:
        storage_service.delete_file(storage_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset exceeds maximum allowed row count of 1,000,000."
        )

    # Normalize column names to avoid spaces, collisions, or special characters
    normalized_cols = normalize_column_names(df.columns.tolist())
    df.columns = normalized_cols

    # Overwrite the saved CSV with clean normalized columns
    df.to_csv(file_path, index=False, encoding="utf-8")
    storage_service.sync_file(storage_key)

    # Compute profiling and schema
    try:
        profile, schema_info = profile_dataframe(df)
    except Exception as e:
        storage_service.delete_file(storage_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data profiling error: {str(e)}"
        )

    dataset_name = name.strip() if name and name.strip() else file.filename.replace(".csv", "")

    dataset = Dataset(
        user_id=current_user.id,
        name=dataset_name,
        storage_key=storage_key,
        original_filename=file.filename,
        file_size=file_size,
        row_count=profile.row_count,
        column_count=profile.column_count,
        schema_json=schema_info,
        profile_json=profile.model_dump(),
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return dataset


@router.get("/{dataset_id}", response_model=DatasetDetail)
def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves dataset details with strict ownership verification."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if dataset.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset.")
    return dataset


@router.get("/{dataset_id}/preview", response_model=DatasetPreview)
def preview_dataset(
    dataset_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns paginated preview rows from the dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if dataset.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset.")

    file_path = storage_service.get_file_path(dataset.storage_key)
    
    # Paginated read
    skip = (page - 1) * page_size
    df = detect_encoding_and_read(str(file_path))
    
    total_rows = len(df)
    page_df = df.iloc[skip:skip + page_size]

    # Convert NaNs to None for clean JSON serialization
    clean_records = page_df.where(pd.notnull(page_df), None).to_dict(orient="records")

    return DatasetPreview(
        columns=df.columns.tolist(),
        rows=clean_records,
        total_rows=total_rows,
        page=page,
        page_size=page_size
    )


@router.get("/{dataset_id}/profile", response_model=DatasetProfile)
def get_dataset_profile(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns comprehensive profiling data for the dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if dataset.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset.")

    if not dataset.profile_json:
        # Re-compute if missing
        file_path = storage_service.get_file_path(dataset.storage_key)
        df = detect_encoding_and_read(str(file_path))
        profile, schema_info = profile_dataframe(df)
        dataset.profile_json = profile.model_dump()
        dataset.schema_json = schema_info
        db.commit()
        return profile

    return DatasetProfile.model_validate(dataset.profile_json)


@router.delete("/{dataset_id}", status_code=status.HTTP_200_OK)
def delete_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deletes dataset and its associated file storage."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if dataset.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this dataset.")

    storage_service.delete_file(dataset.storage_key)
    db.delete(dataset)
    db.commit()

    return {"message": "Dataset successfully deleted."}

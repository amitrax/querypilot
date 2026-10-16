from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class ColumnProfile(BaseModel):
    name: str
    inferred_type: str
    non_null_count: int
    null_count: int
    null_percentage: float
    unique_count: int
    sample_values: List[Any] = []
    # Numeric stats
    mean: Optional[float] = None
    std: Optional[float] = None
    min: Optional[Any] = None
    max: Optional[Any] = None
    median: Optional[float] = None
    q25: Optional[float] = None
    q75: Optional[float] = None
    # Categorical stats
    top_values: Optional[List[Dict[str, Any]]] = None


class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    duplicate_rows: int
    columns: List[ColumnProfile]
    memory_usage_bytes: int


class DatasetBase(BaseModel):
    name: str


class DatasetCreate(DatasetBase):
    pass


class DatasetSummary(DatasetBase):
    id: str
    original_filename: str
    file_size: int
    row_count: int
    column_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class DatasetDetail(DatasetSummary):
    schema_json: Optional[List[Dict[str, Any]]] = None
    profile_json: Optional[DatasetProfile] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class DatasetPreview(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_rows: int
    page: int
    page_size: int

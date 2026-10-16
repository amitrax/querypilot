from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ReportCreate(BaseModel):
    analysis_id: str
    format: str = "csv"  # csv or json


class ReportOut(BaseModel):
    id: str
    user_id: str
    analysis_id: str
    format: str
    status: str
    storage_key: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

from typing import List, Optional, Any, Literal, Dict
from pydantic import BaseModel, Field, ConfigDict


class FilterCondition(BaseModel):
    column: str
    operator: Literal[
        "eq", "neq", "gt", "gte", "lt", "lte",
        "contains", "startswith", "endswith",
        "in", "is_null", "is_not_null"
    ]
    value: Optional[Any] = None


class AggregationSpec(BaseModel):
    column: str
    agg: Literal["sum", "mean", "median", "min", "max", "count", "nunique", "std"]
    alias: Optional[str] = None


class SortSpec(BaseModel):
    column: str
    ascending: bool = True


class ChartConfig(BaseModel):
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    category_column: Optional[str] = None
    value_column: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class AnalysisPlan(BaseModel):
    operation: Literal[
        "aggregate",
        "group_by",
        "filter",
        "sort",
        "correlation",
        "count",
        "describe",
        "value_counts",
        "top_k"
    ] = "aggregate"
    columns: List[str] = Field(default_factory=list)
    filters: List[FilterCondition] = Field(default_factory=list)
    group_by: List[str] = Field(default_factory=list)
    aggregations: List[AggregationSpec] = Field(default_factory=list)
    sort: Optional[SortSpec] = None
    limit: Optional[int] = Field(default=100, ge=1, le=1000)
    chart_type: Optional[Literal["bar", "line", "pie", "scatter", "table", "kpi"]] = None
    chart_config: Optional[ChartConfig] = None
    summary_metric: Optional[str] = None


class AnalysisCreateRequest(BaseModel):
    dataset_id: str
    question: str
    plan_override: Optional[AnalysisPlan] = None


class AnalysisResultData(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_rows: int
    chart_type: Optional[str] = None
    chart_config: Optional[Dict[str, Any]] = None
    kpi_metrics: Optional[Dict[str, Any]] = None
    execution_time_ms: float
    computed_at: str


class AnalysisResponse(BaseModel):
    id: str
    dataset_id: str
    question: str
    status: str  # pending, completed, failed
    analysis_plan: Optional[AnalysisPlan] = None
    error_message: Optional[str] = None
    result: Optional[AnalysisResultData] = None
    explanation: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)

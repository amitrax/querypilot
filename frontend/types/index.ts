export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ColumnProfile {
  name: string;
  inferred_type: string;
  non_null_count: number;
  null_count: number;
  null_percentage: number;
  unique_count: number;
  sample_values: any[];
  mean?: number | null;
  std?: number | null;
  min?: any;
  max?: any;
  median?: number | null;
  q25?: number | null;
  q75?: number | null;
  top_values?: { value: string; count: number }[] | null;
}

export interface DatasetProfile {
  row_count: number;
  column_count: number;
  duplicate_rows: number;
  columns: ColumnProfile[];
  memory_usage_bytes: number;
}

export interface DatasetSummary {
  id: string;
  name: string;
  original_filename: string;
  file_size: number;
  row_count: number;
  column_count: number;
  created_at: string;
  updated_at: string;
}

export interface DatasetDetail extends DatasetSummary {
  schema_json?: { name: string; type: string; nullable: boolean }[];
  profile_json?: DatasetProfile;
}

export interface DatasetPreview {
  columns: string[];
  rows: Record<string, any>[];
  total_rows: number;
  page: number;
  page_size: number;
}

export interface FilterCondition {
  column: string;
  operator: "eq" | "neq" | "gt" | "gte" | "lt" | "lte" | "contains" | "startswith" | "endswith" | "in" | "is_null" | "is_not_null";
  value?: any;
}

export interface AggregationSpec {
  column: string;
  agg: "sum" | "mean" | "median" | "min" | "max" | "count" | "nunique" | "std";
  alias?: string;
}

export interface SortSpec {
  column: string;
  ascending?: boolean;
}

export interface ChartConfig {
  x_axis?: string;
  y_axis?: string;
  category_column?: string;
  value_column?: string;
  title?: string;
  description?: string;
}

export interface AnalysisPlan {
  operation: "aggregate" | "group_by" | "filter" | "sort" | "correlation" | "count" | "describe" | "value_counts" | "top_k";
  columns?: string[];
  filters?: FilterCondition[];
  group_by?: string[];
  aggregations?: AggregationSpec[];
  sort?: SortSpec;
  limit?: number;
  chart_type?: "bar" | "line" | "pie" | "scatter" | "table" | "kpi";
  chart_config?: ChartConfig;
  summary_metric?: string;
}

export interface AnalysisResultData {
  columns: string[];
  rows: Record<string, any>[];
  total_rows: number;
  chart_type?: "bar" | "line" | "pie" | "scatter" | "table" | "kpi";
  chart_config?: ChartConfig;
  kpi_metrics?: Record<string, any>;
  execution_time_ms: number;
  computed_at: string;
}

export interface AnalysisResponse {
  id: string;
  dataset_id: string;
  question: string;
  status: "pending" | "completed" | "failed";
  analysis_plan?: AnalysisPlan;
  error_message?: string;
  result?: AnalysisResultData;
  explanation?: string;
  created_at: string;
}

export interface Report {
  id: string;
  user_id: string;
  analysis_id: string;
  format: string;
  status: string;
  storage_key: string;
  created_at: string;
}

export interface HealthStatus {
  status: string;
  database: string;
  version: string;
  ai_provider: string;
  llm_configured: boolean;
  offline_engine_ready: boolean;
}

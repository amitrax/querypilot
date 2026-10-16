import time
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from app.schemas.analytics import AnalysisPlan, FilterCondition, AnalysisResultData, ChartConfig


class AnalysisEngineError(Exception):
    pass


class AnalysisEngine:
    def __init__(self):
        self.allowed_operators = {
            "eq": lambda s, v: s == v,
            "neq": lambda s, v: s != v,
            "gt": lambda s, v: pd.to_numeric(s, errors="coerce") > float(v),
            "gte": lambda s, v: pd.to_numeric(s, errors="coerce") >= float(v),
            "lt": lambda s, v: pd.to_numeric(s, errors="coerce") < float(v),
            "lte": lambda s, v: pd.to_numeric(s, errors="coerce") <= float(v),
            "contains": lambda s, v: s.astype(str).str.contains(str(v), case=False, na=False),
            "startswith": lambda s, v: s.astype(str).str.startswith(str(v), na=False),
            "endswith": lambda s, v: s.astype(str).str.endswith(str(v), na=False),
            "in": lambda s, v: s.isin(v if isinstance(v, list) else [v]),
            "is_null": lambda s, _: s.isna(),
            "is_not_null": lambda s, _: s.notna(),
        }

    def _clean_for_json(self, value: Any) -> Any:
        """Converts numpy / pandas data types and NaN/Inf to clean JSON serializable types."""
        if pd.isna(value) or value is None:
            return None
        if isinstance(value, (np.integer, int)):
            return int(value)
        if isinstance(value, (np.floating, float)):
            if np.isnan(value) or np.isinf(value):
                return None
            return round(float(value), 4)
        if isinstance(value, (np.bool_, bool)):
            return bool(value)
        if isinstance(value, (pd.Timestamp, np.datetime64)):
            return str(value)
        return str(value)

    def validate_plan(self, df: pd.DataFrame, plan: AnalysisPlan) -> None:
        """Strict validation of plan columns, operators, and aggregations against dataframe."""
        df_cols = set(df.columns)

        # Validate requested columns
        for col in plan.columns:
            if col not in df_cols:
                raise AnalysisEngineError(f"Column '{col}' does not exist in dataset. Available columns: {list(df.columns)}")

        # Validate filter columns & operators
        for f in plan.filters:
            if f.column not in df_cols:
                raise AnalysisEngineError(f"Filter column '{f.column}' does not exist.")
            if f.operator not in self.allowed_operators:
                raise AnalysisEngineError(f"Operator '{f.operator}' is not supported.")

        # Validate group_by
        for gb in plan.group_by:
            if gb not in df_cols:
                raise AnalysisEngineError(f"Group by column '{gb}' does not exist.")

        # Validate aggregations
        for agg in plan.aggregations:
            if agg.column not in df_cols:
                raise AnalysisEngineError(f"Aggregation column '{agg.column}' does not exist.")
            if agg.agg in ["sum", "mean", "median", "std"]:
                if not pd.api.types.is_numeric_dtype(df[agg.column]):
                    raise AnalysisEngineError(f"Cannot perform numeric aggregation '{agg.agg}' on non-numeric column '{agg.column}'.")

        # Validate sort column
        if plan.sort and plan.sort.column not in df_cols and plan.sort.column not in [a.alias or f"{a.column}_{a.agg}" for a in plan.aggregations]:
            # Sort column may be created by aggregation
            pass

    def apply_filters(self, df: pd.DataFrame, filters: List[FilterCondition]) -> pd.DataFrame:
        """Applies allowlisted filter conditions safely."""
        res = df
        for f in filters:
            col_series = res[f.column]
            op_func = self.allowed_operators[f.operator]
            try:
                mask = op_func(col_series, f.value)
                res = res[mask]
            except Exception as e:
                raise AnalysisEngineError(f"Failed applying filter on column '{f.column}': {str(e)}")
        return res

    def execute(self, df: pd.DataFrame, plan: AnalysisPlan) -> AnalysisResultData:
        """
        Executes the plan deterministically using pure pandas operations.
        No eval, no exec, strict column & operator checks.
        """
        start_time = time.perf_counter()
        self.validate_plan(df, plan)

        # Step 1: Filter
        working_df = self.apply_filters(df, plan.filters)

        # Step 2: Main operations
        out_df: pd.DataFrame

        if plan.operation == "count":
            count_val = len(working_df)
            out_df = pd.DataFrame([{"total_count": count_val}])

        elif plan.operation == "correlation":
            numeric_cols = working_df.select_dtypes(include=[np.number]).columns.tolist()
            if len(numeric_cols) < 2:
                raise AnalysisEngineError("At least 2 numeric columns required for correlation analysis.")
            corr_matrix = working_df[numeric_cols].corr().round(4)
            corr_matrix.reset_index(inplace=True)
            corr_matrix.rename(columns={"index": "column"}, inplace=True)
            out_df = corr_matrix

        elif plan.operation == "describe":
            target_cols = plan.columns or working_df.select_dtypes(include=[np.number]).columns.tolist()
            if not target_cols:
                target_cols = working_df.columns.tolist()
            desc = working_df[target_cols].describe(include="all").round(4)
            desc.reset_index(inplace=True)
            desc.rename(columns={"index": "statistic"}, inplace=True)
            out_df = desc

        elif plan.operation == "value_counts":
            col = plan.columns[0] if plan.columns else working_df.columns[0]
            vc = working_df[col].value_counts(dropna=False).head(plan.limit or 20).reset_index()
            vc.columns = [col, "count"]
            out_df = vc

        elif plan.group_by and plan.aggregations:
            # Group By Aggregation
            agg_dict = {}
            rename_map = {}
            for agg in plan.aggregations:
                # pandas groupby agg
                target_key = agg.alias or f"{agg.column}_{agg.agg}"
                agg_dict[target_key] = pd.NamedAgg(column=agg.column, aggfunc=agg.agg)

            grouped = working_df.groupby(plan.group_by, as_index=False).agg(**agg_dict)
            out_df = grouped

        elif plan.aggregations:
            # Global Aggregations (without groupby)
            res_row = {}
            for agg in plan.aggregations:
                col = agg.column
                func = agg.agg
                alias = agg.alias or f"{col}_{func}"
                series = working_df[col].dropna()
                if func == "sum":
                    res_row[alias] = series.sum()
                elif func == "mean":
                    res_row[alias] = series.mean()
                elif func == "median":
                    res_row[alias] = series.median()
                elif func == "min":
                    res_row[alias] = series.min()
                elif func == "max":
                    res_row[alias] = series.max()
                elif func == "count":
                    res_row[alias] = len(series)
                elif func == "nunique":
                    res_row[alias] = series.nunique()
                elif func == "std":
                    res_row[alias] = series.std() if len(series) > 1 else 0.0
            out_df = pd.DataFrame([res_row])

        elif plan.operation == "top_k" or (plan.sort and not plan.group_by):
            # Sorting / Top-K selection
            cols = plan.columns if plan.columns else working_df.columns.tolist()
            out_df = working_df[cols]

        else:
            # Default projection / selection
            cols = plan.columns if plan.columns else working_df.columns.tolist()
            out_df = working_df[cols]

        # Step 3: Sort if requested
        if plan.sort:
            sort_col = plan.sort.column
            if sort_col in out_df.columns:
                out_df = out_df.sort_values(by=sort_col, ascending=plan.sort.ascending)

        # Step 4: Limit
        limit = min(plan.limit or 100, 1000)
        out_df = out_df.head(limit)

        # Step 5: Format result records
        columns = [str(c) for c in out_df.columns]
        rows: List[Dict[str, Any]] = []
        for row in out_df.to_dict(orient="records"):
            cleaned_row = {str(k): self._clean_for_json(v) for k, v in row.items()}
            rows.append(cleaned_row)

        # Step 6: Compute KPI metrics if applicable
        kpi_metrics = None
        if len(rows) > 0 and (plan.operation == "count" or len(plan.aggregations) > 0):
            first_row = rows[0]
            kpi_metrics = {k: v for k, v in first_row.items() if isinstance(v, (int, float))}

        # Step 7: Auto-determine chart configuration if chart_type is specified
        chart_type = plan.chart_type
        chart_config = plan.chart_config.model_dump() if plan.chart_config else None

        if chart_type and not chart_config:
            if len(columns) >= 2:
                chart_config = {
                    "x_axis": columns[0],
                    "y_axis": columns[1],
                    "category_column": columns[0],
                    "value_column": columns[1],
                    "title": f"{columns[1]} by {columns[0]}"
                }
            elif len(columns) == 1:
                chart_config = {
                    "x_axis": columns[0],
                    "y_axis": columns[0],
                    "title": columns[0]
                }

        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return AnalysisResultData(
            columns=columns,
            rows=rows,
            total_rows=len(rows),
            chart_type=chart_type,
            chart_config=chart_config,
            kpi_metrics=kpi_metrics,
            execution_time_ms=execution_time_ms,
            computed_at=pd.Timestamp.now().isoformat(),
        )


analysis_engine = AnalysisEngine()

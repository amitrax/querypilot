import io
import re
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from app.schemas.dataset import DatasetProfile, ColumnProfile


def detect_encoding_and_read(file_path: str, nrows: int | None = None) -> pd.DataFrame:
    """Reads CSV with encoding fallback (utf-8, utf-8-sig, latin1, cp1252)."""
    encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]
    for enc in encodings:
        try:
            df = pd.read_csv(file_path, encoding=enc, nrows=nrows)
            return df
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    # Final fallback attempt with python engine and error replacement
    return pd.read_csv(file_path, encoding="utf-8", errors="replace", on_bad_lines="skip", nrows=nrows)


def normalize_column_names(columns: List[str]) -> List[str]:
    """
    Normalizes column names:
    - Strips leading/trailing spaces
    - Replaces special chars and spaces with underscores
    - Resolves collisions by appending _1, _2, etc.
    """
    normalized = []
    seen = {}
    for col in columns:
        clean = str(col).strip()
        clean = re.sub(r"[^\w\s-]", "", clean)
        clean = re.sub(r"[-\s]+", "_", clean).lower()
        if not clean:
            clean = "col"
        if clean in seen:
            seen[clean] += 1
            unique_name = f"{clean}_{seen[clean]}"
        else:
            seen[clean] = 0
            unique_name = clean
        normalized.append(unique_name)
    return normalized


def profile_dataframe(df: pd.DataFrame) -> Tuple[DatasetProfile, List[Dict[str, Any]]]:
    """
    Computes rigorous profiling statistics on the DataFrame:
    - Row and column counts
    - Duplicate row count
    - Column data types (numeric, categorical, datetime, boolean)
    - Missing value counts & percentages
    - Descriptive stats (mean, std, min, max, median, 25%, 75%)
    - Unique counts & Top frequent values
    """
    total_rows = int(len(df))
    total_cols = int(len(df.columns))
    duplicate_rows = int(df.duplicated().sum()) if total_rows > 0 else 0
    memory_usage = int(df.memory_usage(deep=True).sum()) if total_rows > 0 else 0

    column_profiles: List[ColumnProfile] = []
    schema_info: List[Dict[str, Any]] = []

    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        null_pct = round((null_count / total_rows * 100), 2) if total_rows > 0 else 0.0
        non_null_count = total_rows - null_count
        unique_count = int(series.nunique(dropna=True))

        # Sample values
        sample_vals = series.dropna().head(3).tolist()
        sample_vals = [val if not isinstance(val, (np.generic, pd.Timestamp)) else (val.item() if hasattr(val, "item") else str(val)) for val in sample_vals]

        # Infer type
        inferred_type = "string"
        mean_val = None
        std_val = None
        min_val = None
        max_val = None
        median_val = None
        q25_val = None
        q75_val = None
        top_values = None

        if pd.api.types.is_numeric_dtype(series):
            if pd.api.types.is_bool_dtype(series):
                inferred_type = "boolean"
                # Boolean columns: count True/False, skip numeric percentile stats
                top_counts = series.value_counts(dropna=True).head(5)
                top_values = [{"value": str(k), "count": int(v)} for k, v in top_counts.items()]
            elif pd.api.types.is_integer_dtype(series):
                inferred_type = "integer"
            else:
                inferred_type = "float"

            valid_numeric = series.dropna()
            if len(valid_numeric) > 0 and not pd.api.types.is_bool_dtype(series):
                mean_val = round(float(valid_numeric.mean()), 4)
                std_val = round(float(valid_numeric.std()), 4) if len(valid_numeric) > 1 else 0.0
                min_val = float(valid_numeric.min())
                max_val = float(valid_numeric.max())
                median_val = round(float(valid_numeric.median()), 4)
                q25_val = round(float(valid_numeric.quantile(0.25)), 4)
                q75_val = round(float(valid_numeric.quantile(0.75)), 4)
        elif pd.api.types.is_datetime64_any_dtype(series):
            inferred_type = "datetime"
            valid_dates = series.dropna()
            if len(valid_dates) > 0:
                min_val = str(valid_dates.min())
                max_val = str(valid_dates.max())
        else:
            # Try to detect date/datetime columns stored as strings
            inferred_type = "string"
            top_values = None
            non_null = series.dropna()
            if len(non_null) > 0:
                try:
                    parsed = pd.to_datetime(non_null, errors="coerce")
                    parse_rate = parsed.notna().sum() / len(non_null)
                    if parse_rate >= 0.8:
                        inferred_type = "datetime"
                        min_val = str(parsed.min())
                        max_val = str(parsed.max())
                    else:
                        top_counts = series.value_counts(dropna=True).head(5)
                        top_values = [{"value": str(k), "count": int(v)} for k, v in top_counts.items()]
                except Exception:
                    top_counts = series.value_counts(dropna=True).head(5)
                    top_values = [{"value": str(k), "count": int(v)} for k, v in top_counts.items()]
            else:
                top_counts = series.value_counts(dropna=True).head(5)
                top_values = [{"value": str(k), "count": int(v)} for k, v in top_counts.items()]

        col_profile = ColumnProfile(
            name=str(col),
            inferred_type=inferred_type,
            non_null_count=non_null_count,
            null_count=null_count,
            null_percentage=null_pct,
            unique_count=unique_count,
            sample_values=sample_vals,
            mean=mean_val,
            std=std_val,
            min=min_val,
            max=max_val,
            median=median_val,
            q25=q25_val,
            q75=q75_val,
            top_values=top_values,
        )
        column_profiles.append(col_profile)
        schema_info.append({
            "name": str(col),
            "type": inferred_type,
            "nullable": null_count > 0
        })

    profile = DatasetProfile(
        row_count=total_rows,
        column_count=total_cols,
        duplicate_rows=duplicate_rows,
        columns=column_profiles,
        memory_usage_bytes=memory_usage,
    )

    return profile, schema_info

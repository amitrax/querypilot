import pytest
import pandas as pd
from app.analytics.engine import analysis_engine, AnalysisEngineError
from app.schemas.analytics import AnalysisPlan, AggregationSpec, FilterCondition, SortSpec


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "product": ["Laptop", "Smartphone", "Desk Chair", "Office Desk", "Coffee Maker"],
        "category": ["Electronics", "Electronics", "Furniture", "Furniture", "Appliances"],
        "revenue": [1200.0, 800.0, 250.0, 450.0, 100.0],
        "quantity": [2, 4, 1, 3, 5],
    })


def test_aggregation_without_groupby(sample_df):
    plan = AnalysisPlan(
        operation="aggregate",
        aggregations=[
            AggregationSpec(column="revenue", agg="sum", alias="total_revenue"),
            AggregationSpec(column="revenue", agg="mean", alias="avg_revenue"),
        ]
    )
    result = analysis_engine.execute(sample_df, plan)
    assert result.total_rows == 1
    assert result.rows[0]["total_revenue"] == 2800.0
    assert result.rows[0]["avg_revenue"] == 560.0
    assert result.execution_time_ms > 0


def test_groupby_aggregation_with_sort(sample_df):
    plan = AnalysisPlan(
        operation="group_by",
        group_by=["category"],
        aggregations=[
            AggregationSpec(column="revenue", agg="sum", alias="category_revenue")
        ],
        sort=SortSpec(column="category_revenue", ascending=False),
        limit=5,
        chart_type="bar"
    )
    result = analysis_engine.execute(sample_df, plan)
    assert result.total_rows == 3
    # Electronics has highest revenue (1200 + 800 = 2000)
    assert result.rows[0]["category"] == "Electronics"
    assert result.rows[0]["category_revenue"] == 2000.0
    assert result.chart_type == "bar"


def test_filters(sample_df):
    plan = AnalysisPlan(
        operation="filter",
        filters=[
            FilterCondition(column="revenue", operator="gte", value=500.0)
        ],
        columns=["product", "revenue"]
    )
    result = analysis_engine.execute(sample_df, plan)
    assert result.total_rows == 2
    products = [r["product"] for r in result.rows]
    assert "Laptop" in products
    assert "Smartphone" in products
    assert "Desk Chair" not in products


def test_unknown_column_rejected(sample_df):
    plan = AnalysisPlan(
        operation="aggregate",
        aggregations=[
            AggregationSpec(column="non_existent_col", agg="sum")
        ]
    )
    with pytest.raises(AnalysisEngineError) as exc_info:
        analysis_engine.execute(sample_df, plan)
    assert "non_existent_col" in str(exc_info.value)


def test_numeric_agg_on_string_column_rejected(sample_df):
    plan = AnalysisPlan(
        operation="aggregate",
        aggregations=[
            AggregationSpec(column="product", agg="sum")
        ]
    )
    with pytest.raises(AnalysisEngineError) as exc_info:
        analysis_engine.execute(sample_df, plan)
    assert "non-numeric" in str(exc_info.value)


def test_chart_data_mapping_regression():
    """
    Regression test: verifies that chart-ready row data maps x_axis and y_axis keys
    to the correct per-group revenue_sum values.

    Expected totals (from a 4-product dataset):
      Laptop  → revenue_sum = 20400
      Phone   → revenue_sum = 18300
      Desk    → revenue_sum = 6000
      Chair   → revenue_sum = 5130

    Validates:
    1. Each row's revenue_sum matches the expected value exactly.
    2. chart_config.x_axis == 'product' and chart_config.y_axis == 'revenue_sum'
       so Recharts <Bar dataKey={yKey}> renders each product's actual value.
    3. Rows are sorted descending by revenue_sum (Laptop first).
    """
    df = pd.DataFrame({
        "product": ["Laptop", "Phone", "Desk", "Chair"],
        "revenue": [20400, 18300, 6000, 5130],
    })

    plan = AnalysisPlan(
        operation="group_by",
        group_by=["product"],
        aggregations=[AggregationSpec(column="revenue", agg="sum", alias="revenue_sum")],
        sort=SortSpec(column="revenue_sum", ascending=False),
        limit=10,
        chart_type="bar",
    )

    result = analysis_engine.execute(df, plan)

    # 1. Correct row values
    expected = {"Laptop": 20400, "Phone": 18300, "Desk": 6000, "Chair": 5130}
    assert len(result.rows) == 4
    for row in result.rows:
        product = row["product"]
        assert row["revenue_sum"] == expected[product], (
            f"Chart bar height for '{product}' should be {expected[product]}, "
            f"got {row['revenue_sum']}"
        )

    # 2. Sort order: Laptop is first (highest revenue)
    assert result.rows[0]["product"] == "Laptop"
    assert result.rows[0]["revenue_sum"] == 20400

    # 3. chart_config provides valid x_axis and y_axis keys
    assert result.chart_config is not None
    cc = result.chart_config if isinstance(result.chart_config, dict) else result.chart_config.model_dump()
    assert cc["x_axis"] == "product", f"x_axis should be 'product', got '{cc['x_axis']}'"
    assert cc["y_axis"] == "revenue_sum", f"y_axis should be 'revenue_sum', got '{cc['y_axis']}'"

    # 4. Both x_axis and y_axis values exist in every row (Recharts requirement)
    x_key = cc["x_axis"]
    y_key = cc["y_axis"]
    for row in result.rows:
        assert x_key in row, f"x_axis key '{x_key}' missing from row: {row}"
        assert y_key in row, f"y_axis key '{y_key}' missing from row: {row}"
        assert isinstance(row[y_key], (int, float)), (
            f"y_axis value for '{row[x_key]}' must be numeric for chart rendering, "
            f"got {type(row[y_key])}"
        )

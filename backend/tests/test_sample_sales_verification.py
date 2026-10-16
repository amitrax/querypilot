import os
import pytest
import pandas as pd
from app.analytics.engine import analysis_engine
from app.analytics.exporter import export_analysis_to_csv
from app.ai.provider import HeuristicProvider
from app.schemas.analytics import (
    AnalysisPlan,
    AggregationSpec,
    SortSpec,
)

SAMPLE_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "data", "querypilot_sample_sales.csv"
)


@pytest.fixture
def sample_sales_df():
    assert os.path.exists(SAMPLE_CSV_PATH), f"Missing test fixture: {SAMPLE_CSV_PATH}"
    return pd.read_csv(SAMPLE_CSV_PATH)


class TestQuerypilotSampleSalesRegression:
    """
    Regression test suite for querypilot_sample_sales.csv.
    Verifies that the engine calculates exact mathematical totals without defects,
    and documents why Furniture total is 11,630 (not 11,130).
    """

    def test_actual_csv_integrity_and_duplicate_check(self, sample_sales_df):
        df = sample_sales_df

        # 1. Total row count is exactly 32
        assert len(df) == 32, f"Expected 32 rows, got {len(df)}"

        # 2. Check for duplicate rows across all columns
        duplicates = df[df.duplicated(keep=False)]
        assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate rows in dataset"

        # 3. Check for duplicate order_ids
        order_dupes = df[df.duplicated(subset=["order_id"], keep=False)]
        assert len(order_dupes) == 0, f"Found duplicate order IDs: {order_dupes['order_id'].tolist()}"

        # 4. Verify mathematical consistency: revenue == quantity * unit_price for all 32 rows
        calculated_rev = (df["quantity"] * df["unit_price"]).round(2)
        rev_diff = (df["revenue"].round(2) - calculated_rev).abs()
        assert (rev_diff == 0).all(), "Revenue does not equal quantity * unit_price in some rows"

    def test_category_revenue_calculation(self, sample_sales_df):
        """
        Verify that grouping by category and summing revenue produces:
          - Electronics: 40,700.00
          - Furniture:   11,630.00
        """
        df = sample_sales_df
        plan = AnalysisPlan(
            operation="group_by",
            group_by=["category"],
            aggregations=[
                AggregationSpec(column="revenue", agg="sum", alias="revenue_sum")
            ],
            sort=SortSpec(column="revenue_sum", ascending=False),
            chart_type="bar",
        )

        result = analysis_engine.execute(df, plan)

        assert result.total_rows == 2
        # Verify Electronics
        assert result.rows[0]["category"] == "Electronics"
        assert result.rows[0]["revenue_sum"] == 40700.0

        # Verify Furniture
        assert result.rows[1]["category"] == "Furniture"
        assert result.rows[1]["revenue_sum"] == 11630.0

        # Explanation why Furniture is 11630 and not 11130:
        # In the 32-row dataset:
        # - Desk revenue sum is 6,500.0 (8 orders: 750, 500, 1000, 1250, 250, 750, 1500, 500)
        # - Chair revenue sum is 5,130.0 (8 orders: 720, 540, 900, 630, 810, 450, 360, 720)
        # Total Furniture = 6,500 + 5,130 = 11,630.
        # An expected 11,130 assumed Desk was 6,000 (6,000 + 5,130 = 11,130), which is 500 less
        # than the true Desk sum of 6,500.
        desk_sum = df[df["product"] == "Desk"]["revenue"].sum()
        chair_sum = df[df["product"] == "Chair"]["revenue"].sum()
        assert desk_sum == 6500.0
        assert chair_sum == 5130.0
        assert desk_sum + chair_sum == 11630.0

    def test_product_revenue_calculation(self, sample_sales_df):
        """
        Verify that grouping by product produces:
          - Laptop: 20,400.0
          - Phone:  20,300.0
          - Desk:    6,500.0
          - Chair:   5,130.0
        Total Electronics = 20,400 + 20,300 = 40,700
        Total Furniture   =  6,500 +  5,130 = 11,630
        """
        df = sample_sales_df
        plan = AnalysisPlan(
            operation="group_by",
            group_by=["product"],
            aggregations=[
                AggregationSpec(column="revenue", agg="sum", alias="revenue_sum")
            ],
            sort=SortSpec(column="revenue_sum", ascending=False),
            chart_type="bar",
        )

        result = analysis_engine.execute(df, plan)
        rows_by_prod = {r["product"]: r["revenue_sum"] for r in result.rows}

        assert rows_by_prod["Laptop"] == 20400.0
        assert rows_by_prod["Phone"] == 20300.0
        assert rows_by_prod["Desk"] == 6500.0
        assert rows_by_prod["Chair"] == 5130.0

    def test_heuristic_provider_plan_generation(self, sample_sales_df):
        """
        Verify NLP plan generation on the question 'Which category has the highest total value?'.
        """
        provider = HeuristicProvider()
        schema_info = [
            {"name": col, "type": "float" if col in ("revenue", "unit_price", "cost", "profit") else "string"}
            for col in sample_sales_df.columns
        ]
        sample_records = sample_sales_df.head(5).to_dict(orient="records")

        plan = provider.generate_plan(
            "Which category has the highest total value?",
            schema_info,
            sample_records,
        )

        assert plan.group_by == ["category"]
        assert len(plan.aggregations) >= 1
        assert plan.aggregations[0].column == "revenue"
        assert plan.aggregations[0].agg == "sum"

        result = analysis_engine.execute(sample_sales_df, plan)
        explanation = provider.explain_results(
            "Which category has the highest total value?",
            plan,
            result,
        )

        # Check evidence-backed explanation mentions top entity and exact numbers
        assert "Electronics" in explanation
        assert "40,700.00" in explanation or "40700" in explanation
        assert "Furniture" in explanation
        assert "11,630.00" in explanation or "11630" in explanation

    def test_csv_export_matches_exact_results(self, sample_sales_df):
        """
        Verify that CSV export contains identical computed values as the engine result.
        """
        plan = AnalysisPlan(
            operation="group_by",
            group_by=["category"],
            aggregations=[
                AggregationSpec(column="revenue", agg="sum", alias="revenue_sum")
            ],
            sort=SortSpec(column="revenue_sum", ascending=False),
        )
        result = analysis_engine.execute(sample_sales_df, plan)
        csv_out = export_analysis_to_csv(result.columns, result.rows)
        csv_text = csv_out if isinstance(csv_out, str) else csv_out.decode("utf-8")

        assert "Electronics,40700.0" in csv_text or "Electronics,40700" in csv_text
        assert "Furniture,11630.0" in csv_text or "Furniture,11630" in csv_text

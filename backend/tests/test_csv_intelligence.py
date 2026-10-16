"""
Comprehensive CSV intelligence tests for QueryPilot.

Tests cover:
  - Student marks dataset (education domain)
  - Employee salaries dataset (HR domain)
  - Marketing campaigns dataset (digital marketing domain)
  - Generic numeric / categorical data (non-standard column names)
  - Missing values handling
  - Date / time-series data
  - Ambiguous and unsupported questions
  - Result consistency (text, table, chart, CSV export)
  - Evidence-backed explanations

Each test independently verifies expected results using pandas,
then asserts the engine produces the same answer.
"""

import io
import pytest
import pandas as pd
import numpy as np
from app.analytics.engine import analysis_engine, AnalysisEngineError
from app.analytics.profiler import profile_dataframe
from app.analytics.exporter import export_analysis_to_csv
from app.ai.provider import HeuristicProvider
from app.schemas.analytics import (
    AnalysisPlan,
    AggregationSpec,
    FilterCondition,
    SortSpec,
    ChartConfig,
)


# ============================================================================
# Shared helper
# ============================================================================

def make_schema(df: pd.DataFrame):
    """Profile a DataFrame and return (schema_info, sample_records)."""
    _, schema_info = profile_dataframe(df)
    sample = df.head(5).to_dict(orient="records")
    return schema_info, sample


provider = HeuristicProvider()


# ============================================================================
# Dataset fixtures
# ============================================================================

@pytest.fixture
def students_df():
    """Student marks – education domain, non-standard numeric col names."""
    return pd.DataFrame({
        "student_name": ["Alice", "Bob", "Carol", "Dave", "Eve",
                         "Frank", "Grace", "Hank", "Iris", "Jake"],
        "subject":      ["Math", "Math", "Math", "Math", "Math",
                         "Science", "Science", "Science", "Science", "Science"],
        "marks":        [85, 62, 91, 74, 55, 88, 45, 77, 93, 60],
        "grade":        ["A", "C", "A", "B", "D", "A", "F", "B", "A", "C"],
        "attendance":   [95, 80, 98, 85, 70, 92, 60, 88, 97, 75],
    })


@pytest.fixture
def employees_df():
    """Employee salaries – HR domain."""
    return pd.DataFrame({
        "employee_name": ["Alice", "Bob", "Carol", "Dave", "Eve",
                          "Frank", "Grace", "Hank"],
        "department":    ["Engineering", "Engineering", "HR", "HR",
                          "Marketing", "Marketing", "Finance", "Finance"],
        "salary":        [95000, 88000, 62000, 67000,
                          71000, 76000, 82000, 79000],
        "years_exp":     [5, 3, 8, 6, 4, 7, 9, 5],
        "performance":   [4.2, 3.8, 4.5, 3.9, 4.1, 4.6, 4.3, 4.0],
    })


@pytest.fixture
def campaigns_df():
    """Marketing campaigns – digital marketing domain."""
    return pd.DataFrame({
        "campaign_name": ["Summer Sale", "Back to School", "Black Friday",
                          "New Year", "Spring Launch"],
        "channel":       ["Email", "Social", "Search", "Email", "Social"],
        "spend":         [5000, 8000, 15000, 4500, 7200],
        "impressions":   [120000, 250000, 480000, 95000, 180000],
        "clicks":        [3600, 6250, 14400, 2850, 5400],
        "leads":         [360, 500, 1152, 228, 432],
    })


@pytest.fixture
def generic_df():
    """Generic DataFrame with non-standard, abbreviated column names."""
    return pd.DataFrame({
        "item_id":   [1, 2, 3, 4, 5, 6],
        "lbl":       ["X", "Y", "X", "Z", "Y", "Z"],
        "val_a":     [10.5, 22.0, 8.5, 31.0, 18.0, 27.5],
        "val_b":     [100, 200, 80, 310, 180, 275],
        "flag":      [True, False, True, False, True, False],
    })


@pytest.fixture
def missing_vals_df():
    """DataFrame with deliberate missing values."""
    return pd.DataFrame({
        "student_name": ["Alice", "Bob", "Carol", "Dave", "Eve"],
        "marks":        [85.0, None, 91.0, None, 55.0],
        "grade":        ["A", "C", None, "B", "D"],
    })


@pytest.fixture
def time_series_df():
    """Monthly sales – date-based trend analysis."""
    return pd.DataFrame({
        "month":   ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"],
        "product": ["Widget", "Widget", "Gadget", "Widget", "Gadget", "Widget"],
        "revenue": [12000, 14500, 9800, 16000, 11200, 18500],
        "units":   [120, 145, 98, 160, 112, 185],
    })


# ============================================================================
# SECTION 1 – Student Marks (Education Domain)
# ============================================================================

class TestStudentMarks:

    def test_average_marks_by_subject(self, students_df):
        """Q: What is the average marks by subject?"""
        schema, sample = make_schema(students_df)
        plan = provider.generate_plan(
            "What is the average marks by subject?", schema, sample
        )
        assert plan.operation == "group_by"
        assert "subject" in plan.group_by
        assert any(a.column == "marks" and a.agg == "mean" for a in plan.aggregations)
        assert plan.chart_type in ("bar", "pie")

        result = analysis_engine.execute(students_df, plan)
        # Independent verification
        expected = students_df.groupby("subject")["marks"].mean()
        for row in result.rows:
            subj = row["subject"]
            alias = plan.aggregations[0].alias
            assert abs(row[alias] - expected[subj]) < 0.001, (
                f"Average marks for {subj}: engine={row[alias]:.2f}, "
                f"expected={expected[subj]:.2f}"
            )

    def test_top_student_by_marks(self, students_df):
        """Q: Who has the highest marks? Top row must have the highest aggregated marks."""
        schema, sample = make_schema(students_df)
        plan = provider.generate_plan(
            "Which student has the highest marks?", schema, sample
        )
        result = analysis_engine.execute(students_df, plan)
        assert result.total_rows > 0
        assert plan.sort is not None and plan.sort.ascending is False
        top_row = result.rows[0]
        alias = plan.aggregations[0].alias
        # Top row value must be >= all other rows (it's the maximum aggregated value)
        for row in result.rows:
            assert top_row[alias] >= row[alias], (
                f"Top row has {alias}={top_row[alias]}, but row {row} has higher value"
            )

    def test_students_above_80_marks(self, students_df):
        """Q: Show students who scored above 80 marks."""
        schema, sample = make_schema(students_df)
        plan = provider.generate_plan(
            "Show students who scored above 80 marks", schema, sample
        )
        assert plan.operation == "filter"
        assert any(f.column == "marks" and f.operator == "gt" and f.value == 80.0
                   for f in plan.filters)

        result = analysis_engine.execute(students_df, plan)
        expected_count = int((students_df["marks"] > 80).sum())  # Alice(85),Carol(91),Eve?,Grace(88),Iris(93)
        assert result.total_rows == expected_count, (
            f"Expected {expected_count} students above 80, got {result.total_rows}"
        )

    def test_count_of_records(self, students_df):
        """Q: How many students are in the dataset?"""
        schema, sample = make_schema(students_df)
        plan = provider.generate_plan("How many students are in the dataset?", schema, sample)
        assert plan.operation == "count"
        result = analysis_engine.execute(students_df, plan)
        assert result.rows[0]["total_count"] == 10

    def test_describe_marks(self, students_df):
        """Q: Give me a summary of the marks."""
        schema, sample = make_schema(students_df)
        plan = provider.generate_plan("Give me a summary of the marks", schema, sample)
        assert plan.operation == "describe"
        result = analysis_engine.execute(students_df, plan)
        assert result.total_rows > 0
        assert "marks" in result.columns

    def test_chart_config_keys_present(self, students_df):
        """Chart config x_axis and y_axis must correspond to actual result columns."""
        schema, sample = make_schema(students_df)
        plan = provider.generate_plan(
            "What is the average marks by subject?", schema, sample
        )
        result = analysis_engine.execute(students_df, plan)
        cc = result.chart_config
        assert cc is not None
        if isinstance(cc, dict):
            x, y = cc.get("x_axis"), cc.get("y_axis")
        else:
            x, y = cc.x_axis, cc.y_axis
        assert x in result.columns, f"x_axis '{x}' not in result columns {result.columns}"
        assert y in result.columns, f"y_axis '{y}' not in result columns {result.columns}"


# ============================================================================
# SECTION 2 – Employee Salaries (HR Domain)
# ============================================================================

class TestEmployeeSalaries:

    def test_avg_salary_by_department(self, employees_df):
        """Q: What is the average salary by department?"""
        schema, sample = make_schema(employees_df)
        plan = provider.generate_plan(
            "What is the average salary by department?", schema, sample
        )
        assert plan.operation == "group_by"
        assert "department" in plan.group_by
        assert any(a.agg == "mean" and "salary" in a.column for a in plan.aggregations)

        result = analysis_engine.execute(employees_df, plan)
        expected = employees_df.groupby("department")["salary"].mean()
        alias = plan.aggregations[0].alias
        for row in result.rows:
            dept = row["department"]
            assert abs(row[alias] - expected[dept]) < 0.01

    def test_highest_paid_department(self, employees_df):
        """Q: Which department has the highest average salary?"""
        schema, sample = make_schema(employees_df)
        plan = provider.generate_plan(
            "Which department has the highest average salary?", schema, sample
        )
        result = analysis_engine.execute(employees_df, plan)
        alias = plan.aggregations[0].alias
        # Engineering: (95000+88000)/2 = 91500 – should be highest
        assert result.rows[0]["department"] == "Engineering"
        assert result.rows[0][alias] == pytest.approx(91500.0)

    def test_employees_with_salary_above_80000(self, employees_df):
        """Q: Show employees with salary above 80000."""
        schema, sample = make_schema(employees_df)
        plan = provider.generate_plan(
            "Show employees with salary above 80000", schema, sample
        )
        assert plan.operation == "filter"
        assert any(f.operator in ("gt", "gte") and "salary" in f.column for f in plan.filters)

        result = analysis_engine.execute(employees_df, plan)
        expected = int((employees_df["salary"] > 80000).sum())  # Alice, Bob, Grace, Hank
        assert result.total_rows == expected

    def test_salary_csv_export_consistency(self, employees_df):
        """Result rows and exported CSV must contain the same data."""
        schema, sample = make_schema(employees_df)
        plan = provider.generate_plan(
            "What is the average salary by department?", schema, sample
        )
        result = analysis_engine.execute(employees_df, plan)
        csv_text = export_analysis_to_csv(result.columns, result.rows)

        # Parse CSV back and verify
        csv_df = pd.read_csv(io.StringIO(csv_text))
        assert list(csv_df.columns) == result.columns
        assert len(csv_df) == result.total_rows
        alias = plan.aggregations[0].alias
        for i, row in enumerate(result.rows):
            assert abs(csv_df.iloc[i][alias] - row[alias]) < 0.01, (
                f"CSV row {i} {alias}={csv_df.iloc[i][alias]} "
                f"!= result row {alias}={row[alias]}"
            )

    def test_correlation_salary_experience(self, employees_df):
        """Q: Is there a correlation between salary and experience?"""
        schema, sample = make_schema(employees_df)
        plan = provider.generate_plan(
            "Is there a correlation between salary and years_exp?", schema, sample
        )
        assert plan.operation == "correlation"
        result = analysis_engine.execute(employees_df, plan)
        assert result.total_rows > 0


# ============================================================================
# SECTION 3 – Marketing Campaigns (Digital Marketing Domain)
# ============================================================================

class TestMarketingCampaigns:

    def test_total_spend_by_channel(self, campaigns_df):
        """Q: What is the total spend by channel?"""
        schema, sample = make_schema(campaigns_df)
        plan = provider.generate_plan(
            "What is the total spend by channel?", schema, sample
        )
        assert plan.operation == "group_by"
        assert "channel" in plan.group_by
        agg_cols = [a.column for a in plan.aggregations]
        assert "spend" in agg_cols

        result = analysis_engine.execute(campaigns_df, plan)
        expected = campaigns_df.groupby("channel")["spend"].sum()
        alias = plan.aggregations[0].alias
        for row in result.rows:
            ch = row["channel"]
            assert row[alias] == expected[ch], (
                f"Spend for '{ch}': engine={row[alias]}, expected={expected[ch]}"
            )

    def test_campaign_with_most_leads(self, campaigns_df):
        """Q: Which campaign generated the most leads?"""
        schema, sample = make_schema(campaigns_df)
        plan = provider.generate_plan(
            "Which campaign generated the most leads?", schema, sample
        )
        assert plan.operation == "group_by"
        agg_cols = [a.column for a in plan.aggregations]
        assert "leads" in agg_cols

        result = analysis_engine.execute(campaigns_df, plan)
        alias = plan.aggregations[0].alias
        group_col = plan.group_by[0]  # actual group column chosen by engine
        top = result.rows[0]
        # Top row must have the maximum aggregated leads value
        max_leads = campaigns_df.groupby(group_col)["leads"].sum().max()
        assert top[alias] == pytest.approx(max_leads), (
            f"Top {group_col} should have {max_leads} leads, got {top[alias]}"
        )

    def test_average_clicks_by_channel(self, campaigns_df):
        """Q: What is the average number of clicks per channel?"""
        schema, sample = make_schema(campaigns_df)
        plan = provider.generate_plan(
            "What is the average number of clicks per channel?", schema, sample
        )
        result = analysis_engine.execute(campaigns_df, plan)
        alias = plan.aggregations[0].alias
        expected = campaigns_df.groupby("channel")["clicks"].mean()
        for row in result.rows:
            ch = row["channel"]
            assert abs(row[alias] - expected[ch]) < 0.01

    def test_chart_and_table_consistency(self, campaigns_df):
        """Chart data and the data table must reference the same rows."""
        schema, sample = make_schema(campaigns_df)
        plan = provider.generate_plan(
            "What is the total spend by channel?", schema, sample
        )
        result = analysis_engine.execute(campaigns_df, plan)

        cc = result.chart_config
        if isinstance(cc, dict):
            x_key, y_key = cc.get("x_axis"), cc.get("y_axis")
        else:
            x_key, y_key = cc.x_axis, cc.y_axis

        # Every row must have both keys with correct types
        for row in result.rows:
            assert x_key in row, f"x_axis '{x_key}' missing from row"
            assert y_key in row, f"y_axis '{y_key}' missing from row"
            assert isinstance(row[y_key], (int, float)), (
                f"y_axis '{y_key}' must be numeric, got {type(row[y_key])}"
            )


# ============================================================================
# SECTION 4 – Generic / Abbreviated Column Names
# ============================================================================

class TestGenericColumnNames:

    def test_sum_of_val_a_by_label(self, generic_df):
        """Engine must work with non-standard column names like 'lbl' and 'val_a'."""
        schema, sample = make_schema(generic_df)
        plan = provider.generate_plan(
            "What is the total val_a by lbl?", schema, sample
        )
        result = analysis_engine.execute(generic_df, plan)
        expected = generic_df.groupby("lbl")["val_a"].sum()
        alias = plan.aggregations[0].alias
        for row in result.rows:
            assert abs(row[alias] - expected[row["lbl"]]) < 0.01

    def test_max_val_b_by_label(self, generic_df):
        """Q: What is the maximum val_b for each lbl?"""
        schema, sample = make_schema(generic_df)
        plan = provider.generate_plan(
            "What is the maximum val_b for each lbl?", schema, sample
        )
        result = analysis_engine.execute(generic_df, plan)
        expected = generic_df.groupby("lbl")["val_b"].max()
        alias = plan.aggregations[0].alias
        for row in result.rows:
            assert row[alias] == expected[row["lbl"]]

    def test_first_numeric_col_fallback(self, generic_df):
        """When question has no column mention, engine falls back to first numeric col."""
        schema, sample = make_schema(generic_df)
        # Intentionally vague question – but has a grouping keyword
        plan = provider.generate_plan("Compare totals by lbl", schema, sample)
        result = analysis_engine.execute(generic_df, plan)
        assert result.total_rows > 0


# ============================================================================
# SECTION 5 – Missing Values
# ============================================================================

class TestMissingValues:

    def test_find_missing_marks(self, missing_vals_df):
        """Q: Show records with missing marks."""
        schema, sample = make_schema(missing_vals_df)
        plan = provider.generate_plan(
            "Show records with missing marks", schema, sample
        )
        assert plan.operation == "filter"
        assert any(f.operator == "is_null" for f in plan.filters)

        result = analysis_engine.execute(missing_vals_df, plan)
        # Bob and Dave have null marks
        expected = int(missing_vals_df["marks"].isna().sum())
        assert result.total_rows == expected

    def test_find_null_values_in_marks(self, missing_vals_df):
        """Q: Show records where marks are null (targets the 'marks' column explicitly)."""
        schema, sample = make_schema(missing_vals_df)
        plan = provider.generate_plan("Show records where marks are null", schema, sample)
        assert plan.operation == "filter"
        # The filter must target the 'marks' column
        target_cols = [f.column for f in plan.filters]
        assert "marks" in target_cols, (
            f"Filter should target 'marks' column, got: {target_cols}"
        )
        result = analysis_engine.execute(missing_vals_df, plan)
        assert result.total_rows == 2  # Bob and Dave have null marks

    def test_profiler_counts_missing_accurately(self, missing_vals_df):
        """Profiler must report correct null counts for each column."""
        profile, schema = profile_dataframe(missing_vals_df)
        marks_col = next(c for c in profile.columns if c.name == "marks")
        grade_col  = next(c for c in profile.columns if c.name == "grade")
        assert marks_col.null_count == 2
        assert grade_col.null_count == 1

    def test_aggregate_ignores_nulls(self, missing_vals_df):
        """Sum/mean of marks must skip NaN rows (pandas default behavior)."""
        plan = AnalysisPlan(
            operation="aggregate",
            aggregations=[
                AggregationSpec(column="marks", agg="mean", alias="avg_marks"),
                AggregationSpec(column="marks", agg="sum", alias="total_marks"),
            ],
        )
        result = analysis_engine.execute(missing_vals_df, plan)
        # Non-null marks: 85, 91, 55 → mean=77, sum=231
        assert result.rows[0]["avg_marks"] == pytest.approx(77.0)
        assert result.rows[0]["total_marks"] == pytest.approx(231.0)


# ============================================================================
# SECTION 6 – Time-Series / Date Columns
# ============================================================================

class TestTimeSeries:

    def test_profiler_detects_date_string_column(self, time_series_df):
        """Profiler should classify 'month' (YYYY-MM) as datetime."""
        _, schema = profile_dataframe(time_series_df)
        month_col = next(c for c in schema if c["name"] == "month")
        assert month_col["type"] == "datetime", (
            f"Expected 'month' to be detected as datetime, got '{month_col['type']}'"
        )

    def test_trend_question_selects_line_chart(self, time_series_df):
        """Q: Show revenue trend over time → chart_type=line."""
        schema, sample = make_schema(time_series_df)
        plan = provider.generate_plan(
            "Show the revenue trend over time", schema, sample
        )
        assert plan.chart_type == "line", (
            f"Expected 'line' chart for trend question, got '{plan.chart_type}'"
        )

    def test_monthly_trend_uses_date_as_x_axis(self, time_series_df):
        """The x_axis in chart_config must be the date column."""
        schema, sample = make_schema(time_series_df)
        plan = provider.generate_plan(
            "Show the total revenue by month", schema, sample
        )
        result = analysis_engine.execute(time_series_df, plan)
        cc = result.chart_config
        if isinstance(cc, dict):
            x = cc.get("x_axis")
        else:
            x = cc.x_axis if cc else None
        assert x == "month", f"Expected x_axis='month', got '{x}'"


# ============================================================================
# SECTION 7 – Ambiguous and Unsupported Questions
# ============================================================================

class TestEdgeCases:

    def test_completely_irrelevant_question_raises(self, students_df):
        """A question with zero column/keyword match must raise AnalysisEngineError."""
        schema, sample = make_schema(students_df)
        with pytest.raises(AnalysisEngineError):
            provider.generate_plan(
                "What is the weather in Tokyo tomorrow?", schema, sample
            )

    def test_correlation_requires_two_numeric_cols(self):
        """Correlation on a dataset with only one numeric column must raise."""
        df = pd.DataFrame({
            "name":   ["Alice", "Bob"],
            "salary": [50000, 60000],
        })
        schema, sample = make_schema(df)
        with pytest.raises(AnalysisEngineError, match="Correlation requires"):
            provider.generate_plan(
                "Is there a correlation between salary and experience?", schema, sample
            )

    def test_missing_numeric_col_in_group_by_raises(self):
        """A dataset with only string columns and a sum query must handle gracefully."""
        df = pd.DataFrame({
            "name":   ["Alice", "Bob", "Carol"],
            "status": ["active", "inactive", "active"],
        })
        schema, sample = make_schema(df)
        # No numeric column to aggregate – should raise or return describe fallback
        try:
            plan = provider.generate_plan(
                "What is the total by status?", schema, sample
            )
            # If it produces a plan, it should be describe (fallback)
            assert plan.operation in ("describe", "value_counts", "count")
        except AnalysisEngineError:
            pass  # Explicit error is also acceptable

    def test_top_5_limit_parsed_from_question(self, students_df):
        """Q: Show top 5 students by marks → limit should be 5."""
        schema, sample = make_schema(students_df)
        plan = provider.generate_plan(
            "Show top 5 students by marks", schema, sample
        )
        assert plan.limit == 5

    def test_descending_sort_for_highest(self, students_df):
        """'Highest marks' → ascending=False."""
        schema, sample = make_schema(students_df)
        plan = provider.generate_plan(
            "Which student has the highest marks?", schema, sample
        )
        assert plan.sort is not None
        assert plan.sort.ascending is False

    def test_ascending_sort_for_lowest(self, students_df):
        """'Lowest marks' → ascending=True."""
        schema, sample = make_schema(students_df)
        plan = provider.generate_plan(
            "Who has the lowest marks?", schema, sample
        )
        assert plan.sort is not None
        assert plan.sort.ascending is True


# ============================================================================
# SECTION 8 – Explanation consistency
# ============================================================================

class TestExplanations:

    def test_explanation_references_actual_top_entity(self, employees_df):
        """Explanation must name the actual top department from the result."""
        schema, sample = make_schema(employees_df)
        plan = provider.generate_plan(
            "Which department has the highest average salary?", schema, sample
        )
        result = analysis_engine.execute(employees_df, plan)
        explanation = provider.explain_results(
            "Which department has the highest average salary?", plan, result
        )
        top_dept = result.rows[0]["department"]  # Engineering
        assert top_dept in explanation, (
            f"Explanation should mention '{top_dept}' but got: {explanation}"
        )

    def test_explanation_references_actual_value(self, employees_df):
        """Explanation must contain the actual numeric value, not a fabricated one."""
        schema, sample = make_schema(employees_df)
        plan = provider.generate_plan(
            "What is the average salary by department?", schema, sample
        )
        result = analysis_engine.execute(employees_df, plan)
        alias = plan.aggregations[0].alias
        top_val = result.rows[0][alias]
        explanation = provider.explain_results(
            "What is the average salary by department?", plan, result
        )
        # The formatted value (with comma) must appear in the explanation
        formatted = f"{top_val:,.2f}" if isinstance(top_val, float) else f"{top_val:,}"
        assert formatted in explanation or str(int(top_val)) in explanation, (
            f"Explanation should contain the actual value {formatted}. Got: {explanation}"
        )

    def test_filter_explanation_references_count(self, employees_df):
        """Filter explanation must include the correct row count."""
        schema, sample = make_schema(employees_df)
        plan = provider.generate_plan(
            "Show employees with salary above 80000", schema, sample
        )
        result = analysis_engine.execute(employees_df, plan)
        explanation = provider.explain_results(
            "Show employees with salary above 80000", plan, result
        )
        assert str(result.total_rows) in explanation, (
            f"Explanation should mention count {result.total_rows}. Got: {explanation}"
        )

    def test_empty_result_explanation(self):
        """An empty result must return a meaningful, non-empty explanation string."""
        from app.schemas.analytics import AnalysisResultData
        empty_result = AnalysisResultData(
            columns=["salary_mean"],
            rows=[],
            total_rows=0,
            chart_type="kpi",
            execution_time_ms=1.0,
            computed_at="2024-01-01",
        )
        plan = AnalysisPlan(operation="aggregate",
                            aggregations=[AggregationSpec(column="salary", agg="mean")])
        explanation = provider.explain_results("avg salary", plan, empty_result)
        assert len(explanation) > 10
        assert "no" in explanation.lower() or "zero" in explanation.lower() or "returned" in explanation.lower()


# ============================================================================
# SECTION 9 – CSV export correctness
# ============================================================================

class TestCSVExport:

    def test_csv_column_order_matches_result(self, campaigns_df):
        """CSV headers must match result columns in the same order."""
        schema, sample = make_schema(campaigns_df)
        plan = provider.generate_plan(
            "What is the total spend by channel?", schema, sample
        )
        result = analysis_engine.execute(campaigns_df, plan)
        csv_text = export_analysis_to_csv(result.columns, result.rows)
        csv_df = pd.read_csv(io.StringIO(csv_text))
        assert list(csv_df.columns) == result.columns

    def test_csv_row_values_match_result_rows(self, students_df):
        """Every value in the exported CSV must match the corresponding result row."""
        schema, sample = make_schema(students_df)
        plan = provider.generate_plan(
            "What is the average marks by subject?", schema, sample
        )
        result = analysis_engine.execute(students_df, plan)
        csv_text = export_analysis_to_csv(result.columns, result.rows)
        csv_df = pd.read_csv(io.StringIO(csv_text))
        alias = plan.aggregations[0].alias
        for i, row in enumerate(result.rows):
            assert abs(csv_df.iloc[i][alias] - row[alias]) < 0.01

    def test_csv_formula_injection_in_data(self):
        """Cells starting with = are prefixed with ' in the export."""
        from app.analytics.exporter import sanitize_csv_cell
        malicious = "=SUM(A1:A10)"
        safe = sanitize_csv_cell(malicious)
        assert safe.startswith("'"), f"Formula injection not neutralized: '{safe}'"

    def test_csv_export_handles_none_values(self, missing_vals_df):
        """Exporter must not raise on None values; they become empty strings."""
        plan = AnalysisPlan(
            operation="filter",
            filters=[FilterCondition(column="marks", operator="is_null")],
            columns=["student_name", "marks", "grade"],
        )
        result = analysis_engine.execute(missing_vals_df, plan)
        csv_text = export_analysis_to_csv(result.columns, result.rows)
        assert csv_text  # non-empty
        assert "student_name" in csv_text

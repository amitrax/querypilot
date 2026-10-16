"""
AI Provider module for QueryPilot.

Provides two implementations:
  - HeuristicProvider: fully offline, deterministic, schema-driven NLP query planner.
  - ExternalLLMProvider: wraps any OpenAI-compatible API with graceful fallback.
"""
import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings
from app.schemas.analytics import (
    AnalysisPlan,
    FilterCondition,
    AggregationSpec,
    SortSpec,
    ChartConfig,
    AnalysisResultData,
)
from app.analytics.engine import AnalysisEngineError


# ---------------------------------------------------------------------------
# Vocabulary tables – domain-agnostic, covers sales, HR, education, marketing
# ---------------------------------------------------------------------------

# Numeric metric keywords → candidate column name fragments (ordered by priority)
METRIC_VOCAB: List[str] = [
    # financial / sales
    "revenue", "sales", "amount", "total", "profit", "cost", "price",
    "spend", "budget", "expense", "income", "earning",
    # HR / payroll
    "salary", "wage", "compensation", "pay",
    # education
    "marks", "mark", "score", "grade", "gpa", "percentage", "points", "result",
    # marketing / digital
    "impressions", "clicks", "leads", "conversions", "views", "reach",
    "engagement", "ctr", "roas", "roi",
    # generic numeric
    "value", "count", "qty", "quantity", "units", "number",
]

# Categorical grouping dimension keywords → candidate column name fragments
DIMENSION_VOCAB: List[str] = [
    # product / business
    "product", "category", "brand", "item", "sku", "segment",
    # geography
    "region", "country", "state", "city", "location", "area", "zone",
    # org / HR
    "department", "dept", "team", "division", "role", "position", "title",
    "employee", "staff", "person",
    # education
    "student", "name", "course", "subject", "class", "grade", "school",
    # marketing
    "campaign", "channel", "platform", "source", "medium", "ad",
    # time (for groupby on string date cols)
    "month", "quarter", "year", "week", "date", "period",
    # generic
    "type", "group", "label", "status", "gender",
]

# Keywords that trigger agg_func selection
AGG_KEYWORDS: Dict[str, List[str]] = {
    "mean":   ["average", "avg", "mean", "typical"],
    "median": ["median", "middle"],
    "min":    ["minimum", "least", "cheapest", "smallest", "lowest paid",
               "lowest scoring", "lowest earning", "lowest spending"],
    "max":    ["maximum", "most", "peak", "highest paid", "highest scoring",
               "highest earning", "top earning"],
    "count":  ["count", "number of", "how many records", "frequency"],
    "std":    ["standard deviation", "std", "variance", "spread"],
    "nunique": ["unique", "distinct", "different"],
}

# Keywords that suggest "highest / descending" sort intent
DESCENDING_KEYWORDS = ["highest", "top", "best", "most", "maximum", "peak",
                       "largest", "greatest", "leading", "dominant", "highest paid",
                       "highest scoring", "richest", "expensive"]
ASCENDING_KEYWORDS  = ["lowest", "bottom", "worst", "least", "minimum", "smallest",
                       "cheapest", "ascending", "fewest"]


class BaseAIProvider(ABC):
    @abstractmethod
    def generate_plan(
        self,
        question: str,
        schema_info: List[Dict[str, Any]],
        sample_data: List[Dict[str, Any]],
    ) -> AnalysisPlan:
        """Translates a natural-language question into a validated AnalysisPlan."""

    @abstractmethod
    def explain_results(
        self,
        question: str,
        plan: AnalysisPlan,
        result: AnalysisResultData,
    ) -> str:
        """Produces an evidence-backed explanation of computed results.
        Must ONLY reference numbers that exist in `result`; never fabricate."""


class HeuristicProvider(BaseAIProvider):
    """
    Deterministic, schema-driven NLP planner.

    Works with ANY column names – does not assume 'product', 'revenue', etc.
    Column matching priority:
      1. Column name mentioned verbatim in the question.
      2. Column name is a substring of the question (or vice-versa).
      3. Column inferred from domain vocabulary against the schema.
      4. First column of the appropriate type.
    """

    # ------------------------------------------------------------------ #
    # Column-matching helpers                                              #
    # ------------------------------------------------------------------ #

    def _find_best_column(
        self,
        candidate_names: List[str],
        schema_columns: List[Dict[str, Any]],
        numeric_only: bool = False,
    ) -> Optional[str]:
        """Match a list of candidate name fragments against actual schema columns."""
        allowed_types = ["integer", "float"] if numeric_only else None
        cols = [
            c["name"] for c in schema_columns
            if (allowed_types is None or c["type"] in allowed_types)
        ]
        lower_map = {c.lower(): c for c in cols}

        # 1. Exact match
        for name in candidate_names:
            if name.lower() in lower_map:
                return lower_map[name.lower()]

        # 2. Substring match (both directions)
        for name in candidate_names:
            for c in cols:
                if name.lower() in c.lower() or c.lower() in name.lower():
                    return c

        return None

    def _cols_mentioned_in_question(
        self, q_lower: str, col_list: List[str]
    ) -> List[str]:
        """Return all columns whose name appears verbatim (case-insensitive) in the question."""
        return [c for c in col_list if c.lower() in q_lower]

    def _infer_metric_column(
        self,
        q_lower: str,
        schema_info: List[Dict[str, Any]],
        num_cols: List[str],
    ) -> Optional[str]:
        """
        Infer which numeric column the question targets.
        Priority: verbatim mention → vocab match → first numeric column.
        """
        # Verbatim mention
        mentioned = self._cols_mentioned_in_question(q_lower, num_cols)
        if mentioned:
            return mentioned[0]
        # Vocab match
        col = self._find_best_column(METRIC_VOCAB, schema_info, numeric_only=True)
        if col:
            return col
        return num_cols[0] if num_cols else None

    def _infer_group_column(
        self,
        q_lower: str,
        schema_info: List[Dict[str, Any]],
        cat_cols: List[str],
    ) -> Optional[str]:
        """
        Infer which categorical / text column to group by.
        Priority: verbatim mention → vocab match → first categorical column.
        """
        mentioned = self._cols_mentioned_in_question(q_lower, cat_cols)
        if mentioned:
            return mentioned[0]
        col = self._find_best_column(DIMENSION_VOCAB, schema_info)
        if col:
            # Only accept if it is actually categorical
            cat_lower = {c.lower(): c for c in cat_cols}
            if col.lower() in cat_lower:
                return cat_lower[col.lower()]
        return cat_cols[0] if cat_cols else None

    def _detect_agg_func(self, q_lower: str) -> str:
        """Return the aggregation function implied by the question."""
        for func, keywords in AGG_KEYWORDS.items():
            if any(kw in q_lower for kw in keywords):
                return func
        return "sum"  # default

    def _detect_sort_direction(self, q_lower: str) -> bool:
        """True → ascending, False → descending (default for top/highest queries)."""
        if any(kw in q_lower for kw in ASCENDING_KEYWORDS):
            return True
        # Default to descending for ranking/comparison questions
        return False

    def _detect_limit(self, q_lower: str, default: int = 10) -> int:
        m = re.search(r"\btop\s+(\d+)\b", q_lower)
        if m:
            return int(m.group(1))
        m = re.search(r"\bbottom\s+(\d+)\b", q_lower)
        if m:
            return int(m.group(1))
        return default

    def _has_date_col(self, schema_info: List[Dict[str, Any]]) -> bool:
        return any(c["type"] in ("datetime",) for c in schema_info)

    def _infer_date_col(self, schema_info: List[Dict[str, Any]]) -> Optional[str]:
        for c in schema_info:
            if c["type"] == "datetime":
                return c["name"]
        # Try string cols whose name hints at date
        for c in schema_info:
            if c["type"] == "string" and any(
                kw in c["name"].lower()
                for kw in ["date", "time", "month", "year", "period", "week", "quarter"]
            ):
                return c["name"]
        return None

    # ------------------------------------------------------------------ #
    # Range / threshold extraction                                         #
    # ------------------------------------------------------------------ #

    def _extract_numeric_threshold(self, q_lower: str) -> Optional[float]:
        """Extract a numeric threshold from phrases like 'above 70', 'more than 50000'."""
        patterns = [
            r"(?:above|over|more than|greater than|>)\s*(\d+(?:\.\d+)?)",
            r"(?:below|under|less than|fewer than|<)\s*(\d+(?:\.\d+)?)",
            r"(?:at least|minimum of)\s*(\d+(?:\.\d+)?)",
            r"(?:at most|maximum of|up to)\s*(\d+(?:\.\d+)?)",
        ]
        for pat in patterns:
            m = re.search(pat, q_lower)
            if m:
                return float(m.group(1))
        return None

    def _extract_threshold_operator(self, q_lower: str) -> str:
        """Return the filter operator implied by the threshold phrase."""
        if re.search(r"\b(?:above|over|more than|greater than)\b", q_lower):
            return "gt"
        if re.search(r"\b(?:below|under|less than|fewer than)\b", q_lower):
            return "lt"
        if re.search(r"\b(?:at least|minimum of)\b", q_lower):
            return "gte"
        if re.search(r"\b(?:at most|maximum of|up to)\b", q_lower):
            return "lte"
        return "gt"

    # ------------------------------------------------------------------ #
    # Main plan generator                                                  #
    # ------------------------------------------------------------------ #

    def generate_plan(
        self,
        question: str,
        schema_info: List[Dict[str, Any]],
        sample_data: List[Dict[str, Any]],
    ) -> AnalysisPlan:
        q_lower = question.lower()
        all_cols  = [c["name"] for c in schema_info]
        num_cols  = [c["name"] for c in schema_info if c["type"] in ("integer", "float")]
        cat_cols  = [c["name"] for c in schema_info if c["type"] in ("string", "category", "boolean")]
        date_cols = [c["name"] for c in schema_info if c["type"] == "datetime"]

        # Verbatim column matches from question text
        matched_num = self._cols_mentioned_in_question(q_lower, num_cols)
        matched_cat = self._cols_mentioned_in_question(q_lower, cat_cols)

        # ── Relevance gate ──────────────────────────────────────────────
        analytical_keywords = [
            # aggregation / stats
            "total", "sum", "average", "avg", "mean", "median", "max", "min",
            "highest", "lowest", "top", "bottom", "best", "worst", "peak",
            # grouping
            "by", "per", "group", "each", "compare", "breakdown", "across",
            # counting
            "how many", "count", "number of", "frequency", "distribution",
            # ranking
            "rank", "ranking", "most", "least", "leading",
            # time
            "trend", "over time", "monthly", "quarterly", "yearly", "weekly",
            # quality
            "missing", "null", "empty", "incomplete",
            # exploration
            "summary", "describe", "overview", "statistics", "profile",
            # relationships
            "correlat", "relationship", "impact", "effect",
            # threshold
            "above", "below", "over", "under", "more than", "less than",
            "greater", "smaller", "at least", "at most",
            # domain vocab (fast path)
            *METRIC_VOCAB[:20],
        ]
        has_col_mention = bool(
            matched_num or matched_cat
            or any(c.lower() in q_lower for c in all_cols)
        )
        has_keyword = any(k in q_lower for k in analytical_keywords)

        if not has_col_mention and not has_keyword:
            raise AnalysisEngineError(
                f"The question is ambiguous or could not be mapped to the columns in this dataset. "
                f"Please clarify your question. Available columns: {all_cols}. "
                f"Try asking about specific columns or use terms like "
                f"'average', 'total', 'highest', 'compare by', 'missing values', etc."
            )

        # ── 1. Correlation ──────────────────────────────────────────────
        if "correlat" in q_lower or "relationship between" in q_lower:
            if len(num_cols) >= 2:
                return AnalysisPlan(operation="correlation", chart_type="table")
            raise AnalysisEngineError(
                "Correlation requires at least 2 numeric columns; "
                f"this dataset has: {num_cols or 'none'}."
            )

        # ── 2. Missing values ───────────────────────────────────────────
        if "missing" in q_lower or "null" in q_lower or "empty" in q_lower or "incomplete" in q_lower:
            # Target a specific column if named, else show whole dataset filter
            target_col = (
                matched_num[0] if matched_num
                else (matched_cat[0] if matched_cat
                      else all_cols[0])
            )
            return AnalysisPlan(
                operation="filter",
                filters=[FilterCondition(column=target_col, operator="is_null")],
                columns=all_cols[:8],
                chart_type="table",
            )

        # ── 3. Describe / summary ───────────────────────────────────────
        if any(w in q_lower for w in ("summary", "describe", "overview", "statistics", "profile", "distribution of")):
            cols_to_describe = matched_num or num_cols or all_cols[:6]
            return AnalysisPlan(
                operation="describe",
                columns=cols_to_describe[:8],
                chart_type="table",
            )

        # ── 4. Count – total records or filtered count ──────────────────
        is_count_q = any(
            phrase in q_lower
            for phrase in ("how many", "total number", "number of records", "count of")
        )
        # "how many X scored above Y" → filtered count, not bare count
        has_threshold = self._extract_numeric_threshold(q_lower) is not None
        if is_count_q and not has_threshold and not any(
            k in q_lower for k in ("by", "per", "each", "group", "across", "top", "highest", "lowest")
        ):
            return AnalysisPlan(operation="count", chart_type="kpi")

        # ── 5. Threshold / range filter  ───────────────────────────────
        # e.g. "students who scored above 80", "employees with salary > 60000"
        if has_threshold and not any(
            k in q_lower for k in ("average", "mean", "total", "sum", "by", "per", "each")
        ):
            threshold = self._extract_numeric_threshold(q_lower)
            op = self._extract_threshold_operator(q_lower)
            target_num = self._infer_metric_column(q_lower, schema_info, num_cols)
            if target_num and threshold is not None:
                return AnalysisPlan(
                    operation="filter",
                    filters=[FilterCondition(column=target_num, operator=op, value=threshold)],
                    columns=all_cols[:8],
                    chart_type="table",
                )

        # ── 6. Value counts / frequency distribution ────────────────────
        if any(w in q_lower for w in ("frequency", "how many in each", "breakdown of", "split by")):
            group_col = self._infer_group_column(q_lower, schema_info, cat_cols)
            if group_col:
                return AnalysisPlan(
                    operation="value_counts",
                    columns=[group_col],
                    limit=20,
                    chart_type="bar",
                    chart_config=ChartConfig(
                        x_axis=group_col,
                        y_axis="count",
                        title=f"Frequency of {group_col}",
                    ),
                )

        # ── 7. Time-trend (line chart) ──────────────────────────────────
        is_trend = any(w in q_lower for w in ("trend", "over time", "monthly", "by month",
                                               "quarterly", "by quarter", "weekly", "by week",
                                               "by year", "yearly", "by date"))
        if is_trend:
            date_col = self._infer_date_col(schema_info)
            target_metric = self._infer_metric_column(q_lower, schema_info, num_cols)
            if date_col and target_metric:
                agg_func = self._detect_agg_func(q_lower)
                alias = f"{target_metric}_{agg_func}"
                return AnalysisPlan(
                    operation="group_by",
                    group_by=[date_col],
                    aggregations=[AggregationSpec(column=target_metric, agg=agg_func, alias=alias)],
                    sort=SortSpec(column=date_col, ascending=True),
                    limit=100,
                    chart_type="line",
                    chart_config=ChartConfig(
                        x_axis=date_col,
                        y_axis=alias,
                        title=f"{agg_func.capitalize()} of {target_metric} over time",
                    ),
                )

        # ── 8. Group-by aggregation (most common analytical path) ────────
        target_metric = self._infer_metric_column(q_lower, schema_info, num_cols)
        group_col = self._infer_group_column(q_lower, schema_info, cat_cols)
        agg_func = self._detect_agg_func(q_lower)
        ascending = self._detect_sort_direction(q_lower)
        limit = self._detect_limit(q_lower)

        if group_col and target_metric:
            # Don't sum/mean a column that's also used as groupby (edge case)
            if target_metric == group_col:
                target_metric = num_cols[0] if num_cols else None
            if target_metric is None:
                raise AnalysisEngineError(
                    f"Could not find a numeric column to aggregate. "
                    f"Available numeric columns: {num_cols or 'none'}."
                )

            alias = f"{target_metric}_{agg_func}"

            chart_type = "bar"
            if "pie" in q_lower or "proportion" in q_lower or "share" in q_lower:
                chart_type = "pie"

            return AnalysisPlan(
                operation="group_by",
                group_by=[group_col],
                aggregations=[AggregationSpec(column=target_metric, agg=agg_func, alias=alias)],
                sort=SortSpec(column=alias, ascending=ascending),
                limit=limit,
                chart_type=chart_type,
                chart_config=ChartConfig(
                    x_axis=group_col,
                    y_axis=alias,
                    category_column=group_col,
                    value_column=alias,
                    title=f"{agg_func.capitalize()} of {target_metric} by {group_col}",
                ),
            )

        # ── 9. Single-metric global aggregation ─────────────────────────
        if target_metric:
            alias = f"{target_metric}_{agg_func}"
            return AnalysisPlan(
                operation="aggregate",
                aggregations=[AggregationSpec(column=target_metric, agg=agg_func, alias=alias)],
                chart_type="kpi",
            )

        # ── 10. Fallback: general preview ───────────────────────────────
        return AnalysisPlan(
            operation="describe",
            columns=all_cols[:6],
            limit=20,
            chart_type="table",
        )

    # ------------------------------------------------------------------ #
    # Explanation generator (evidence-backed, no hallucination)            #
    # ------------------------------------------------------------------ #

    def explain_results(
        self,
        question: str,
        plan: AnalysisPlan,
        result: AnalysisResultData,
    ) -> str:
        rows = result.rows
        if not rows:
            return (
                f"The query was evaluated but returned no matching records. "
                f"This may mean the filter threshold is outside the range of the data, "
                f"or there are no non-null values in the target column."
            )

        # ── Count ───────────────────────────────────────────────────────
        if plan.operation == "count":
            cnt = rows[0].get("total_count", 0)
            return f"The dataset contains **{cnt:,}** records in total."

        # ── Correlation ─────────────────────────────────────────────────
        if plan.operation == "correlation":
            n_cols = len(result.columns) - 1
            return (
                f"Pearson correlation computed across **{n_cols}** numeric columns. "
                "Values near **+1.0** indicate strong positive relationships; "
                "values near **-1.0** indicate strong negative relationships; "
                "values near **0** indicate little linear association."
            )

        # ── Describe ────────────────────────────────────────────────────
        if plan.operation == "describe":
            return (
                f"Statistical summary computed for **{len(result.columns) - 1}** columns "
                f"across **{result.total_rows}** descriptive statistics "
                f"(count, mean, std, min, 25%, median, 75%, max)."
            )

        # ── Filter (missing values / threshold) ─────────────────────────
        if plan.operation == "filter":
            n = result.total_rows
            if plan.filters:
                f0 = plan.filters[0]
                if f0.operator in ("is_null",):
                    return (
                        f"Found **{n}** record(s) with missing values in column **{f0.column}**. "
                        f"These rows may need cleaning before analysis."
                    )
                else:
                    op_text = {
                        "gt": "greater than", "gte": "at least",
                        "lt": "less than", "lte": "at most",
                    }.get(f0.operator, f0.operator)
                    return (
                        f"**{n}** record(s) satisfy the condition: "
                        f"**{f0.column}** {op_text} **{f0.value}**."
                    )
            return f"Filter returned **{n}** matching record(s)."

        # ── Group-by aggregation ─────────────────────────────────────────
        if plan.group_by and plan.aggregations and rows:
            group_col = plan.group_by[0]
            agg_spec = plan.aggregations[0]
            val_col = agg_spec.alias or f"{agg_spec.column}_{agg_spec.agg}"

            top_row = rows[0]
            top_entity = top_row.get(group_col, "—")
            top_val = top_row.get(val_col)
            formatted_val = (
                f"{top_val:,.2f}" if isinstance(top_val, float)
                else f"{top_val:,}" if isinstance(top_val, int)
                else str(top_val)
            )

            n_groups = result.total_rows
            agg_label = {
                "sum": "total", "mean": "average", "median": "median",
                "min": "minimum", "max": "maximum", "count": "count",
                "std": "standard deviation", "nunique": "unique count",
            }.get(agg_spec.agg, agg_spec.agg)

            # Build evidence-backed insight
            insight = (
                f"Based on verified computation across **{n_groups}** group(s), "
                f"**{top_entity}** has the highest {agg_label} of **{agg_spec.column}** "
                f"at **{formatted_val}**."
            )

            # Add range context if multiple groups exist
            if n_groups >= 2:
                bottom_row = rows[-1]
                bottom_entity = bottom_row.get(group_col, "—")
                bottom_val = bottom_row.get(val_col)
                if bottom_val is not None and top_val is not None and bottom_val != top_val:
                    bottom_fmt = (
                        f"{bottom_val:,.2f}" if isinstance(bottom_val, float)
                        else f"{bottom_val:,}" if isinstance(bottom_val, int)
                        else str(bottom_val)
                    )
                    insight += (
                        f" **{bottom_entity}** has the lowest at **{bottom_fmt}**."
                    )

            return insight

        # ── Global aggregate ─────────────────────────────────────────────
        if plan.aggregations and rows:
            row = rows[0]
            parts = []
            for k, v in row.items():
                if isinstance(v, float):
                    parts.append(f"{k}: **{v:,.2f}**")
                elif isinstance(v, int):
                    parts.append(f"{k}: **{v:,}**")
                else:
                    parts.append(f"{k}: **{v}**")
            return f"Computed aggregate result — {', '.join(parts)}."

        # ── Default ──────────────────────────────────────────────────────
        return (
            f"Query executed successfully. "
            f"**{result.total_rows}** record(s) returned for: \"{question}\"."
        )


# ---------------------------------------------------------------------------
# External LLM Provider
# ---------------------------------------------------------------------------

class ExternalLLMProvider(BaseAIProvider):
    """
    Connects to an OpenAI-compatible API (or Gemini) when configured.
    Falls back gracefully to HeuristicProvider on any failure.
    """

    def __init__(self, fallback: HeuristicProvider):
        self.fallback = fallback
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL or "gpt-4o-mini"
        self.base_url = settings.LLM_BASE_URL or "https://api.openai.com/v1"

    def _call_llm(self, prompt: str, system_prompt: str) -> Optional[str]:
        if not self.api_key:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"} if "gpt" in self.model else None,
            }
            with httpx.Client(timeout=15.0) as client:
                res = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
        except Exception:
            return None
        return None

    def generate_plan(
        self,
        question: str,
        schema_info: List[Dict[str, Any]],
        sample_data: List[Dict[str, Any]],
    ) -> AnalysisPlan:
        if not self.api_key:
            return self.fallback.generate_plan(question, schema_info, sample_data)

        system_prompt = (
            "You are QueryPilot's analytical planner. Translate natural language questions "
            "about a dataset into a structured JSON AnalysisPlan. "
            "ONLY use columns that exist in the schema. Return strictly JSON matching: "
            '{"operation": "group_by"|"aggregate"|"filter"|"sort"|"correlation"|"count"|"describe"|"value_counts"|"top_k", '
            '"columns": [], "filters": [{"column": "", "operator": "eq"|"gt"|"lt"|"gte"|"lte"|"neq"|"contains"|"is_null"|"is_not_null", "value": ""}], '
            '"group_by": [], "aggregations": [{"column": "", "agg": "sum"|"mean"|"median"|"min"|"max"|"count"|"nunique"|"std", "alias": ""}], '
            '"sort": {"column": "", "ascending": false}, "limit": 10, '
            '"chart_type": "bar"|"line"|"pie"|"scatter"|"table"|"kpi"}'
        )

        user_content = (
            f"Question: {question}\n"
            f"Schema: {json.dumps(schema_info)}\n"
            f"Sample rows: {json.dumps(sample_data[:3])}"
        )
        response = self._call_llm(user_content, system_prompt)

        if response:
            try:
                parsed = json.loads(response)
                return AnalysisPlan.model_validate(parsed)
            except Exception:
                pass

        return self.fallback.generate_plan(question, schema_info, sample_data)

    def explain_results(
        self,
        question: str,
        plan: AnalysisPlan,
        result: AnalysisResultData,
    ) -> str:
        if not self.api_key:
            return self.fallback.explain_results(question, plan, result)

        system_prompt = (
            "You are a data analyst explaining verified computational results. "
            "CRITICAL: Only cite numbers from the result data. Do NOT invent any figures. "
            "Be concise (2–3 sentences). Highlight the key finding."
        )
        user_content = (
            f"Question: {question}\n"
            f"Result rows (verified): {json.dumps(result.rows[:5])}\n"
            f"Columns: {result.columns}"
        )
        response = self._call_llm(user_content, system_prompt)
        if response and len(response.strip()) > 10:
            return response.strip()

        return self.fallback.explain_results(question, plan, result)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_ai_provider() -> BaseAIProvider:
    heuristic = HeuristicProvider()
    if settings.AI_PROVIDER != "heuristic" and settings.LLM_API_KEY:
        return ExternalLLMProvider(fallback=heuristic)
    return heuristic

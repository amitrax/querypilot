"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { DatasetSummary, DatasetDetail, AnalysisResponse, Report } from "@/types";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import {
  Database,
  BarChart2,
  FileSpreadsheet,
  UploadCloud,
  ArrowRight,
  TrendingUp,
  Activity,
  CheckCircle2,
  Calendar,
  Layers,
  Sparkles,
  ArrowUpRight,
  Info,
  Clock,
  Filter,
} from "lucide-react";
import { FormattedText } from "@/components/FormattedText";

export default function DashboardPage() {
  const router = useRouter();
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [analyses, setAnalyses] = useState<AnalysisResponse[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("");
  const [selectedDatasetDetail, setSelectedDatasetDetail] = useState<DatasetDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    async function loadInitialData() {
      try {
        setLoading(true);
        const [dsList, ansList, repList] = await Promise.all([
          api.getDatasets(),
          api.getAnalyses(),
          api.getReports().catch(() => []),
        ]);
        setDatasets(dsList);
        setAnalyses(ansList);
        setReports(repList);

        if (dsList.length > 0) {
          setSelectedDatasetId(dsList[0].id);
        }
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadInitialData();
  }, []);

  // Fetch details for the selected dataset when selection changes
  useEffect(() => {
    if (!selectedDatasetId) {
      setSelectedDatasetDetail(null);
      return;
    }
    let isCancelled = false;
    async function fetchDetail() {
      try {
        setDetailLoading(true);
        const detail = await api.getDataset(selectedDatasetId);
        if (!isCancelled) {
          setSelectedDatasetDetail(detail);
        }
      } catch (err) {
        console.error("Failed to load dataset detail:", err);
      } finally {
        if (!isCancelled) setDetailLoading(false);
      }
    }
    fetchDetail();
    return () => {
      isCancelled = true;
    };
  }, [selectedDatasetId]);

  // Total summary metrics
  const totalRecords = useMemo(
    () => datasets.reduce((acc, d) => acc + (d.row_count || 0), 0),
    [datasets]
  );

  // Analyses filtered for selected dataset
  const datasetAnalyses = useMemo(
    () => analyses.filter((a) => a.dataset_id === selectedDatasetId),
    [analyses, selectedDatasetId]
  );

  // Columns & schema categorization for selected dataset
  const columnsProfile = selectedDatasetDetail?.profile_json?.columns || [];
  const categoricalCols = useMemo(
    () =>
      columnsProfile.filter(
        (c) =>
          c.inferred_type === "string" ||
          c.inferred_type === "category" ||
          c.inferred_type === "text"
      ),
    [columnsProfile]
  );
  const numericCols = useMemo(
    () =>
      columnsProfile.filter(
        (c) =>
          c.inferred_type === "integer" ||
          c.inferred_type === "float" ||
          c.inferred_type === "numeric"
      ),
    [columnsProfile]
  );
  const dateCols = useMemo(
    () =>
      columnsProfile.filter(
        (c) =>
          c.inferred_type === "datetime" ||
          c.inferred_type === "date" ||
          c.name.toLowerCase().includes("date") ||
          c.name.toLowerCase().includes("time") ||
          c.name.toLowerCase().includes("day") ||
          c.name.toLowerCase().includes("month")
      ),
    [columnsProfile]
  );

  // Primary Breakdown Chart Data (derived from actual analysis or top categorical values)
  const breakdownChartData = useMemo(() => {
    // 1. First priority: look for a completed bar or aggregation analysis for this dataset
    const barAnalysis = datasetAnalyses.find(
      (a) =>
        a.result?.rows &&
        a.result.rows.length > 0 &&
        (a.result.chart_type === "bar" || a.result.chart_type === "pie" || a.result.columns?.length >= 2)
    );

    if (barAnalysis && barAnalysis.result) {
      const cfg = barAnalysis.result.chart_config || {};
      const xKey = cfg.x_axis || barAnalysis.result.columns[0];
      const yKey = cfg.y_axis || barAnalysis.result.columns[1] || barAnalysis.result.columns[0];

      return {
        title: cfg.title || barAnalysis.question,
        xKey,
        yKey,
        data: barAnalysis.result.rows.slice(0, 10).map((row) => ({
          name: String(row[xKey] ?? "Unknown"),
          value: typeof row[yKey] === "number" ? row[yKey] : Number(row[yKey]) || 0,
        })),
        source: "analysis",
      };
    }

    // 2. Second priority: use top_values from first categorical column profile
    const firstCat = categoricalCols.find((c) => c.top_values && c.top_values.length > 0);
    if (firstCat && firstCat.top_values) {
      return {
        title: `Frequency Distribution: ${firstCat.name}`,
        xKey: firstCat.name,
        yKey: "Frequency",
        data: firstCat.top_values.slice(0, 8).map((item) => ({
          name: String(item.value),
          value: item.count,
        })),
        source: "profile",
      };
    }

    // 3. Fallback: numeric column averages if available
    if (numericCols.length > 0) {
      return {
        title: "Numeric Column Averages",
        xKey: "Metric",
        yKey: "Mean Value",
        data: numericCols.slice(0, 6).map((c) => ({
          name: c.name,
          value: c.mean ?? 0,
        })),
        source: "profile",
      };
    }

    return null;
  }, [datasetAnalyses, categoricalCols, numericCols]);

  // Time-Series or Trend Chart Data (derived from actual time-series analysis or date column)
  const timeSeriesChartData = useMemo(() => {
    // 1. Look for analysis with line chart or time trend
    const lineAnalysis = datasetAnalyses.find(
      (a) =>
        a.result?.rows &&
        a.result.rows.length > 0 &&
        (a.result.chart_type === "line" ||
          a.question.toLowerCase().includes("trend") ||
          a.question.toLowerCase().includes("month") ||
          a.question.toLowerCase().includes("date"))
    );

    if (lineAnalysis && lineAnalysis.result) {
      const cfg = lineAnalysis.result.chart_config || {};
      const xKey = cfg.x_axis || lineAnalysis.result.columns[0];
      const yKey = cfg.y_axis || lineAnalysis.result.columns[1];
      return {
        title: cfg.title || lineAnalysis.question,
        xKey,
        yKey,
        data: lineAnalysis.result.rows.slice(0, 15).map((row) => ({
          time: String(row[xKey] ?? ""),
          value: typeof row[yKey] === "number" ? row[yKey] : Number(row[yKey]) || 0,
        })),
        hasDateSupport: true,
      };
    }

    // 2. Check if selected dataset has date columns
    if (dateCols.length > 0 && numericCols.length > 0) {
      return {
        title: `Trend Readiness: ${dateCols[0].name} (${numericCols[0].name})`,
        xKey: dateCols[0].name,
        yKey: numericCols[0].name,
        data: [],
        hasDateSupport: true,
        promptSuggestion: `Show trends of ${numericCols[0].name} by ${dateCols[0].name}`,
      };
    }

    return {
      title: "Temporal Analysis",
      hasDateSupport: false,
      data: [],
    };
  }, [datasetAnalyses, dateCols, numericCols]);

  // Suggested questions based on selected dataset schema
  const suggestedQueries = useMemo(() => {
    if (!selectedDatasetDetail) return [];
    const queries: string[] = [];
    const cat = categoricalCols[0]?.name;
    const num = numericCols[0]?.name;
    const num2 = numericCols[1]?.name;
    const date = dateCols[0]?.name;

    if (cat && num) {
      queries.push(`What is the total ${num} by ${cat}?`);
      queries.push(`Which ${cat} has the highest ${num}?`);
    } else if (num) {
      queries.push(`What is the average ${num}?`);
    }

    if (date && num) {
      queries.push(`Show monthly trends for ${num}`);
    }

    if (num && num2) {
      queries.push(`Find correlation between ${num} and ${num2}`);
    }

    queries.push("Check for missing or null values");
    return queries.slice(0, 4);
  }, [selectedDatasetDetail, categoricalCols, numericCols, dateCols]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
          <span className="text-xs font-medium text-slate-500">Loading analytics workspace...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Welcome & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Analytics Overview
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Real-time telemetry, dataset schema intelligence, and verified analytical metrics.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Link
            href="/dashboard/datasets"
            className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 hover:text-slate-900 transition-all"
          >
            <UploadCloud className="h-4 w-4 text-blue-600" />
            <span>Upload CSV</span>
          </Link>
          <Link
            href="/dashboard/workspace"
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 active:scale-[0.98] transition-all"
          >
            <span>Ask a Question</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>

      {/* KPI Metric Summary Cards (Clean Light Cards with subtle borders & soft shadows) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Datasets */}
        <div className="saas-card p-5">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Total Datasets
            </span>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
              <Database className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">{datasets.length}</span>
            <span className="text-xs text-slate-500">active tables</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400">
            {datasets.length > 0
              ? `Latest: ${datasets[0].name.slice(0, 20)}`
              : "No datasets uploaded yet"}
          </div>
        </div>

        {/* Card 2: Rows Profiled */}
        <div className="saas-card p-5">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Rows Profiled
            </span>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">
              {totalRecords.toLocaleString()}
            </span>
            <span className="text-xs text-slate-500">records</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400">
            Automatic type inference & null audits
          </div>
        </div>

        {/* Card 3: Completed Analyses */}
        <div className="saas-card p-5">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Completed Analyses
            </span>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
              <BarChart2 className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">{analyses.length}</span>
            <span className="text-xs text-slate-500">queries executed</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400">
            100% deterministic pandas execution
          </div>
        </div>

        {/* Card 4: Reports & Exports */}
        <div className="saas-card p-5">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Reports & Exports
            </span>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-50 text-purple-600">
              <FileSpreadsheet className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">{reports.length}</span>
            <span className="text-xs text-slate-500">sanitized files</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-400">
            Formula injection defense enabled
          </div>
        </div>
      </div>

      {/* Analytics Area with Dataset Selector and Real Schema-Derived Visualizations */}
      <div className="saas-card p-6">
        {/* Section Header & Dataset Selector */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900">
                Dataset Visual Intelligence
              </h2>
              <span className="saas-badge bg-blue-50 text-blue-700 border border-blue-100">
                Live Data
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Visual analytics generated dynamically from your selected dataset schema.
            </p>
          </div>

          {datasets.length > 0 && (
            <div className="flex items-center gap-2">
              <label htmlFor="dataset-select" className="text-xs font-medium text-slate-600">
                Dataset:
              </label>
              <select
                id="dataset-select"
                value={selectedDatasetId}
                onChange={(e) => setSelectedDatasetId(e.target.value)}
                className="text-xs font-medium rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-slate-800 shadow-2xs focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.row_count} rows, {d.column_count} cols)
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Empty state when no datasets */}
        {datasets.length === 0 ? (
          <div className="py-16 text-center">
            <Database className="mx-auto h-12 w-12 text-slate-300 mb-3" />
            <h3 className="text-sm font-semibold text-slate-800">No datasets available</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
              Upload a CSV file to explore automated visualizations, schema profiling, and natural-language query capabilities.
            </p>
            <Link
              href="/dashboard/datasets"
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 transition-colors"
            >
              <UploadCloud className="h-4 w-4" />
              <span>Upload CSV Dataset</span>
            </Link>
          </div>
        ) : (
          <div className="pt-5 space-y-6">
            {/* Dataset Metadata Strip */}
            {selectedDatasetDetail && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 rounded-lg bg-slate-50/80 border border-slate-100 text-xs">
                <div>
                  <span className="text-slate-400 block text-[11px]">Rows & Columns</span>
                  <span className="font-semibold text-slate-800">
                    {selectedDatasetDetail.row_count.toLocaleString()} rows × {selectedDatasetDetail.column_count} cols
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Dimensions (Categorical)</span>
                  <span className="font-semibold text-slate-800">
                    {categoricalCols.length} columns ({categoricalCols.map((c) => c.name).slice(0, 2).join(", ") || "None"})
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Measures (Numeric)</span>
                  <span className="font-semibold text-slate-800">
                    {numericCols.length} columns ({numericCols.map((c) => c.name).slice(0, 2).join(", ") || "None"})
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Temporal (Date/Time)</span>
                  <span className="font-semibold text-slate-800">
                    {dateCols.length > 0 ? `${dateCols.length} detected (${dateCols[0].name})` : "None"}
                  </span>
                </div>
              </div>
            )}

            {/* Visual Charts Grid (Derived directly from selected dataset) */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Chart 1: Breakdown / Primary Distribution Chart */}
              <div className="rounded-xl border border-slate-200/90 bg-white p-4 flex flex-col justify-between">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-xs font-bold text-slate-900">
                      {breakdownChartData?.title || "Category Breakdown"}
                    </h3>
                    <span className="text-[11px] text-slate-400">
                      {breakdownChartData?.source === "analysis"
                        ? "Source: Verified Analytical Execution"
                        : "Source: Dataset Column Profile"}
                    </span>
                  </div>
                  <Link
                    href={`/dashboard/workspace?dataset=${selectedDatasetId}`}
                    className="text-[11px] font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1"
                  >
                    <span>Explore in Workspace</span>
                    <ArrowUpRight className="h-3 w-3" />
                  </Link>
                </div>

                <div className="h-64 w-full">
                  {breakdownChartData && breakdownChartData.data.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={breakdownChartData.data}
                        margin={{ top: 10, right: 10, left: 0, bottom: 25 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis
                          dataKey="name"
                          tick={{ fill: "#64748b", fontSize: 11 }}
                          tickLine={false}
                          axisLine={{ stroke: "#e2e8f0" }}
                          interval={0}
                          angle={-20}
                          textAnchor="end"
                        />
                        <YAxis
                          tick={{ fill: "#64748b", fontSize: 11 }}
                          tickLine={false}
                          axisLine={{ stroke: "#e2e8f0" }}
                          tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v)}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#ffffff",
                            borderColor: "#e2e8f0",
                            borderRadius: "0.5rem",
                            fontSize: "12px",
                            boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05)",
                          }}
                          formatter={(value: any) => [
                            typeof value === "number" ? value.toLocaleString() : value,
                            breakdownChartData.yKey,
                          ]}
                        />
                        <Bar
                          dataKey="value"
                          name={breakdownChartData.yKey}
                          fill="#3b82f6"
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex h-full flex-col items-center justify-center text-center text-slate-400">
                      <BarChart2 className="h-8 w-8 text-slate-300 mb-2" />
                      <p className="text-xs">No categorical distribution available for this dataset.</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Chart 2: Time-Series / Temporal Trends (Or Column Null Analysis if no date) */}
              <div className="rounded-xl border border-slate-200/90 bg-white p-4 flex flex-col justify-between">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-xs font-bold text-slate-900">
                      {timeSeriesChartData.title}
                    </h3>
                    <span className="text-[11px] text-slate-400">
                      {timeSeriesChartData.hasDateSupport
                        ? "Temporal Trend Analysis"
                        : "Dataset Schema Characteristic"}
                    </span>
                  </div>
                  {timeSeriesChartData.hasDateSupport && (
                    <span className="saas-badge bg-emerald-50 text-emerald-700 text-[10px]">
                      Date Supported
                    </span>
                  )}
                </div>

                <div className="h-64 w-full flex items-center justify-center">
                  {timeSeriesChartData.data && timeSeriesChartData.data.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={timeSeriesChartData.data}
                        margin={{ top: 10, right: 10, left: 0, bottom: 25 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis
                          dataKey="time"
                          tick={{ fill: "#64748b", fontSize: 11 }}
                          tickLine={false}
                          axisLine={{ stroke: "#e2e8f0" }}
                          angle={-20}
                          textAnchor="end"
                        />
                        <YAxis
                          tick={{ fill: "#64748b", fontSize: 11 }}
                          tickLine={false}
                          axisLine={{ stroke: "#e2e8f0" }}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#ffffff",
                            borderColor: "#e2e8f0",
                            borderRadius: "0.5rem",
                            fontSize: "12px",
                            boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05)",
                          }}
                        />
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke="#2563eb"
                          strokeWidth={2}
                          dot={{ r: 3, fill: "#2563eb" }}
                          activeDot={{ r: 5 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : timeSeriesChartData.hasDateSupport ? (
                    <div className="text-center p-6 bg-slate-50/60 rounded-lg border border-dashed border-slate-200">
                      <Calendar className="mx-auto h-8 w-8 text-blue-500 mb-2" />
                      <p className="text-xs font-semibold text-slate-700">Date field detected</p>
                      <p className="text-[11px] text-slate-500 mt-1 max-w-xs mx-auto">
                        This dataset contains temporal data. Ask a trend-based question to compute the time-series curve.
                      </p>
                      <button
                        onClick={() =>
                          router.push(
                            `/dashboard/workspace?dataset=${selectedDatasetId}&q=${encodeURIComponent(
                              timeSeriesChartData.promptSuggestion || "Show trends over time"
                            )}`
                          )
                        }
                        className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors"
                      >
                        <span>Compute Time-Series Trend</span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className="text-center p-6 bg-slate-50/60 rounded-lg border border-slate-200">
                      <Info className="mx-auto h-7 w-7 text-slate-400 mb-2" />
                      <p className="text-xs font-semibold text-slate-700">No Date/Time Fields</p>
                      <p className="text-[11px] text-slate-500 mt-1 max-w-xs mx-auto">
                        This dataset consists strictly of cross-sectional categorical and numeric variables. Time-series charts are suppressed to prevent inaccurate projections.
                      </p>
                      <div className="mt-3 inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-md">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>Schema-accurate behavior</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Quick Analytical Suggestions */}
            {suggestedQueries.length > 0 && (
              <div className="pt-2">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="h-3.5 w-3.5 text-blue-600" />
                  <span className="text-xs font-semibold text-slate-700">
                    Suggested Questions for this Dataset:
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {suggestedQueries.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() =>
                        router.push(
                          `/dashboard/workspace?dataset=${selectedDatasetId}&q=${encodeURIComponent(q)}`
                        )
                      }
                      className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-1.5 text-xs text-slate-700 hover:border-blue-300 hover:bg-blue-50/50 hover:text-blue-700 transition-all text-left"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Lower Dual Grid: Recent Datasets & Recent Analyses */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Datasets Table */}
        <div className="saas-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
              <div className="flex items-center gap-2.5">
                <Database className="h-4 w-4 text-blue-600" />
                <h3 className="font-bold text-sm text-slate-900">Recent Datasets</h3>
              </div>
              <Link
                href="/dashboard/datasets"
                className="text-xs font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                <span>View all</span>
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            {datasets.length === 0 ? (
              <div className="py-8 text-center text-slate-400 text-xs">
                No datasets uploaded yet.
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {datasets.slice(0, 5).map((d) => (
                  <div
                    key={d.id}
                    className="py-3 flex items-center justify-between hover:bg-slate-50/60 px-2 rounded-lg transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                        <FileSpreadsheet className="h-4 w-4" />
                      </div>
                      <div>
                        <h4 className="text-xs font-semibold text-slate-900">{d.name}</h4>
                        <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
                          <span>{d.row_count.toLocaleString()} rows</span>
                          <span>•</span>
                          <span>{d.column_count} cols</span>
                          <span>•</span>
                          <span>{(d.file_size / 1024).toFixed(1)} KB</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/dashboard/datasets/${d.id}`}
                        className="px-2.5 py-1 text-[11px] font-medium text-slate-600 hover:text-slate-900 rounded border border-slate-200 bg-white hover:bg-slate-50 transition-colors"
                      >
                        Profile
                      </Link>
                      <Link
                        href={`/dashboard/workspace?dataset=${d.id}`}
                        className="px-2.5 py-1 text-[11px] font-medium text-blue-700 rounded border border-blue-200 bg-blue-50 hover:bg-blue-100 transition-colors"
                      >
                        Query
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Recent Analyses Activity */}
        <div className="saas-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
              <div className="flex items-center gap-2.5">
                <BarChart2 className="h-4 w-4 text-indigo-600" />
                <h3 className="font-bold text-sm text-slate-900">Recent Analyses</h3>
              </div>
              <Link
                href="/dashboard/history"
                className="text-xs font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                <span>View all</span>
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            {analyses.length === 0 ? (
              <div className="py-8 text-center text-slate-400 text-xs">
                No analyses performed yet.
              </div>
            ) : (
              <div className="space-y-3">
                {analyses.slice(0, 5).map((a) => (
                  <div
                    key={a.id}
                    className="p-3 rounded-lg border border-slate-100 bg-slate-50/50 hover:border-slate-200 hover:bg-slate-50 transition-all"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-slate-800 line-clamp-1 max-w-xs">
                        {a.question}
                      </span>
                      <span className="saas-badge bg-emerald-50 text-emerald-700 text-[10px]">
                        {a.result?.execution_time_ms ? `${a.result.execution_time_ms} ms` : "Verified"}
                      </span>
                    </div>
                    {a.explanation && (
                      <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
                        <FormattedText text={a.explanation} />
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

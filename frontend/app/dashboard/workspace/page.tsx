"use client";

import React, { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { DatasetSummary, AnalysisResponse } from "@/types";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import {
  Sparkles,
  Terminal,
  Send,
  Download,
  BarChart2,
  TrendingUp,
  Table as TableIcon,
  Code2,
  Clock,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  Layers,
  Database,
  ArrowUpRight,
} from "lucide-react";
import { FormattedText } from "@/components/FormattedText";

const CHART_COLORS = [
  "#3b82f6",
  "#06b6d4",
  "#10b981",
  "#8b5cf6",
  "#f59e0b",
  "#ec4899",
  "#f43f5e",
];

const DEFAULT_QUESTIONS = [
  "Which category has the highest total value?",
  "Show trend over time",
  "What is the average of numeric columns?",
  "Compare distribution across groups",
  "Check for missing or null values",
];

export default function WorkspacePage() {
  const searchParams = useSearchParams();
  const initialDatasetId = searchParams.get("dataset") || "";
  const initialQuery = searchParams.get("q") || "";

  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>(initialDatasetId);
  const [question, setQuestion] = useState(initialQuery);
  const [executing, setExecuting] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [reportSuccess, setReportSuccess] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<"chart" | "table" | "plan">("chart");
  const [selectedChartType, setSelectedChartType] = useState<string>("bar");

  useEffect(() => {
    async function loadDatasets() {
      try {
        const list = await api.getDatasets();
        setDatasets(list);
        if (list.length > 0 && !selectedDatasetId) {
          setSelectedDatasetId(list[0].id);
        }
      } catch (err) {
        console.error("Failed to load datasets:", err);
      }
    }
    loadDatasets();
  }, [selectedDatasetId]);

  // If initial query was passed in URL params, auto-execute once dataset is ready
  useEffect(() => {
    if (initialQuery && selectedDatasetId && !analysis && !executing) {
      handleRunAnalysis(initialQuery);
    }
  }, [initialQuery, selectedDatasetId]);

  const handleRunAnalysis = async (queryText?: string) => {
    const q = (queryText || question).trim();
    if (!q) return;
    if (!selectedDatasetId) {
      setError("Please select a target dataset to query.");
      return;
    }

    setError(null);
    setReportSuccess(null);
    setExecuting(true);

    try {
      const res = await api.createAnalysis(selectedDatasetId, q);
      setAnalysis(res);
      if (res.result?.chart_type) {
        setSelectedChartType(res.result.chart_type);
      }
      setQuestion(q);
    } catch (err: any) {
      setError(err.message || "Failed to execute analysis.");
    } finally {
      setExecuting(false);
    }
  };

  const handleExportCSV = async () => {
    if (!analysis) return;
    try {
      setExporting(true);
      const rep = await api.createReport(analysis.id, "csv");
      setReportSuccess(`Report saved! Downloading formula-safe CSV...`);
      window.open(api.getReportDownloadUrl(rep.id), "_blank");
    } catch (err: any) {
      setError(err.message || "Failed to export report.");
    } finally {
      setExporting(false);
    }
  };

  const resultData = analysis?.result;
  const rows = resultData?.rows || [];
  const columns = resultData?.columns || [];

  // Determine chart X and Y keys
  const xKey = useMemo(() => {
    if (resultData?.chart_config?.x_axis && columns.includes(resultData.chart_config.x_axis)) {
      return resultData.chart_config.x_axis;
    }
    return columns[0] || "";
  }, [resultData, columns]);

  const yKey = useMemo(() => {
    if (resultData?.chart_config?.y_axis && columns.includes(resultData.chart_config.y_axis)) {
      return resultData.chart_config.y_axis;
    }
    return columns[1] || columns[0] || "";
  }, [resultData, columns]);

  const selectedDataset = datasets.find((d) => d.id === selectedDatasetId);

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2">
        <div>
          <div className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 mb-1.5">
            <Sparkles className="h-3 w-3" />
            <span>AI Analytical Copilot</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Analysis Workspace
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Natural-language queries compiled into deterministic, verified pandas operations.
          </p>
        </div>

        {/* Dataset Target Selector */}
        <div className="flex items-center gap-2.5">
          <label className="text-xs font-semibold text-slate-600">Target Dataset:</label>
          <div className="relative">
            <select
              value={selectedDatasetId}
              onChange={(e) => setSelectedDatasetId(e.target.value)}
              className="appearance-none rounded-lg border border-slate-200 bg-white py-2 pl-3.5 pr-9 text-xs font-semibold text-slate-800 shadow-2xs focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.row_count} rows, {d.column_count} cols)
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
          </div>
        </div>
      </div>

      {/* Query Bar Card */}
      <div className="saas-card p-5">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleRunAnalysis();
          }}
          className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3"
        >
          <div className="relative flex-1">
            <Terminal className="pointer-events-none absolute left-3.5 top-3.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about your data (e.g. 'Which product generated the highest revenue?')"
              className="w-full rounded-lg border border-slate-200 bg-slate-50/60 py-2.5 pl-10 pr-4 text-xs font-medium text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all"
            />
          </div>
          <button
            type="submit"
            disabled={executing || !question.trim()}
            className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 active:scale-[0.98] transition-all disabled:opacity-40"
          >
            {executing ? (
              <span className="flex items-center gap-2">
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                <span>Computing...</span>
              </span>
            ) : (
              <span className="flex items-center gap-1.5">
                <span>Run Analysis</span>
                <Send className="h-3.5 w-3.5" />
              </span>
            )}
          </button>
        </form>

        {/* Example Prompt Chips */}
        <div className="mt-4 flex flex-wrap items-center gap-2 pt-3 border-t border-slate-100">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mr-1">
            Suggested:
          </span>
          {DEFAULT_QUESTIONS.map((q, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQuestion(q);
                handleRunAnalysis(q);
              }}
              className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Notifications / Alerts */}
      {error && (
        <div className="flex items-center gap-2.5 rounded-lg border border-red-200 bg-red-50 p-4 text-xs text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
          <span>{error}</span>
        </div>
      )}

      {reportSuccess && (
        <div className="flex items-center gap-2.5 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-800">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
          <span>{reportSuccess}</span>
        </div>
      )}

      {/* Loading Skeleton */}
      {executing && (
        <div className="saas-card p-12 text-center">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600 mb-3 animate-pulse">
            <Sparkles className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">
            Translating Intent into Verified Plan
          </h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Mapping requested columns against dataset schema, executing pandas aggregation, and formatting verified charts...
          </p>
        </div>
      )}

      {/* Analysis Results View */}
      {analysis && !executing && (
        <div className="space-y-6">
          {/* Executive Finding Card */}
          <div className="saas-card p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3.5 mb-4">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Verified Analytical Finding
                </span>
                <span className="saas-badge bg-blue-50 text-blue-700 text-[10px]">
                  100% Deterministic
                </span>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 text-xs text-slate-500 font-mono">
                  <Clock className="h-3.5 w-3.5 text-slate-400" />
                  <span>{resultData?.execution_time_ms} ms</span>
                </div>
                <button
                  onClick={handleExportCSV}
                  disabled={exporting}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 hover:text-slate-900 transition-colors disabled:opacity-50"
                >
                  <Download className="h-3.5 w-3.5 text-slate-500" />
                  <span>{exporting ? "Exporting..." : "Export CSV"}</span>
                </button>
              </div>
            </div>

            <div className="text-xs sm:text-sm text-slate-800 leading-relaxed font-medium">
              <FormattedText text={analysis.explanation || "Computation completed successfully."} />
            </div>
          </div>

          {/* Visualization, Table & Execution Plan Card */}
          <div className="saas-card p-6">
            {/* View Switcher Controls */}
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4 mb-6">
              <div className="flex items-center gap-1 rounded-lg bg-slate-100/80 p-1 border border-slate-200">
                <button
                  onClick={() => setActiveView("chart")}
                  className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                    activeView === "chart"
                      ? "bg-white text-blue-700 shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  <BarChart2 className="h-3.5 w-3.5" />
                  <span>Visualization</span>
                </button>
                <button
                  onClick={() => setActiveView("table")}
                  className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                    activeView === "table"
                      ? "bg-white text-blue-700 shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  <TableIcon className="h-3.5 w-3.5" />
                  <span>Data Table</span>
                </button>
                <button
                  onClick={() => setActiveView("plan")}
                  className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                    activeView === "plan"
                      ? "bg-white text-blue-700 shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  <Code2 className="h-3.5 w-3.5" />
                  <span>Engine Plan</span>
                </button>
              </div>

              {/* Chart Type Toggle (When on chart view) */}
              {activeView === "chart" && (
                <div className="flex items-center gap-1 text-xs">
                  <span className="text-slate-400 mr-1 text-[11px]">Type:</span>
                  <button
                    onClick={() => setSelectedChartType("bar")}
                    className={`rounded-md px-2.5 py-1 font-medium border ${
                      selectedChartType === "bar"
                        ? "border-blue-300 bg-blue-50 text-blue-700"
                        : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    Bar
                  </button>
                  <button
                    onClick={() => setSelectedChartType("line")}
                    className={`rounded-md px-2.5 py-1 font-medium border ${
                      selectedChartType === "line"
                        ? "border-blue-300 bg-blue-50 text-blue-700"
                        : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    Line
                  </button>
                  <button
                    onClick={() => setSelectedChartType("pie")}
                    className={`rounded-md px-2.5 py-1 font-medium border ${
                      selectedChartType === "pie"
                        ? "border-blue-300 bg-blue-50 text-blue-700"
                        : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    Pie
                  </button>
                </div>
              )}
            </div>

            {/* TAB 1: RECHARTS VISUALIZATION */}
            {activeView === "chart" && (
              <div className="w-full h-80 min-h-[320px]">
                {rows.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-xs text-slate-400">
                    No records found to render for this query.
                  </div>
                ) : selectedChartType === "bar" ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={rows} margin={{ top: 20, right: 30, left: 20, bottom: 25 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis
                        dataKey={xKey}
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        tickLine={false}
                        axisLine={{ stroke: "#e2e8f0" }}
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
                          color: "#0f172a",
                          fontSize: "12px",
                          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05)",
                        }}
                      />
                      <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                      <Bar dataKey={yKey} fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : selectedChartType === "line" ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={rows} margin={{ top: 20, right: 30, left: 20, bottom: 25 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis
                        dataKey={xKey}
                        tick={{ fill: "#64748b", fontSize: 11 }}
                        tickLine={false}
                        axisLine={{ stroke: "#e2e8f0" }}
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
                          color: "#0f172a",
                          fontSize: "12px",
                          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05)",
                        }}
                      />
                      <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                      <Line
                        type="monotone"
                        dataKey={yKey}
                        stroke="#2563eb"
                        strokeWidth={2.5}
                        dot={{ r: 4, fill: "#2563eb" }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#ffffff",
                          borderColor: "#e2e8f0",
                          borderRadius: "0.5rem",
                          color: "#0f172a",
                          fontSize: "12px",
                          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05)",
                        }}
                      />
                      <Legend wrapperStyle={{ fontSize: "12px" }} />
                      <Pie
                        data={rows}
                        dataKey={yKey}
                        nameKey={xKey}
                        cx="50%"
                        cy="50%"
                        outerRadius={95}
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      >
                        {rows.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={CHART_COLORS[index % CHART_COLORS.length]}
                          />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
            )}

            {/* TAB 2: DATA TABLE */}
            {activeView === "table" && (
              <div className="overflow-x-auto rounded-lg border border-slate-200">
                <table className="w-full text-left text-xs text-slate-800">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase text-[11px]">
                    <tr>
                      <th className="px-4 py-2.5 w-12 text-slate-400">#</th>
                      {columns.map((col) => (
                        <th key={col} className="px-4 py-2.5 text-slate-700">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {rows.map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                        <td className="px-4 py-2 text-slate-400">{idx + 1}</td>
                        {columns.map((col) => (
                          <td key={col} className="px-4 py-2 whitespace-nowrap text-slate-900">
                            {row[col] !== null && row[col] !== undefined ? String(row[col]) : "null"}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* TAB 3: ENGINE PLAN INSPECTOR */}
            {activeView === "plan" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>Structured plan compiled for deterministic execution:</span>
                  <span className="text-emerald-700 font-semibold flex items-center gap-1">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Strict Column Whitelist Validated
                  </span>
                </div>
                <pre className="rounded-lg border border-slate-200 bg-slate-900 p-4 font-mono text-xs text-emerald-400 overflow-x-auto shadow-inner">
                  {JSON.stringify(analysis.analysis_plan, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

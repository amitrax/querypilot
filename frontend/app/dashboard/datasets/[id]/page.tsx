"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { DatasetDetail, DatasetPreview, DatasetProfile } from "@/types";
import {
  Database,
  ArrowLeft,
  Terminal,
  Table as TableIcon,
  PieChart,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  FileSpreadsheet,
  AlertTriangle,
  Info,
} from "lucide-react";

export default function DatasetDetailPage() {
  const params = useParams();
  const router = useRouter();
  const datasetId = params.id as string;

  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [activeTab, setActiveTab] = useState<"profile" | "preview">("profile");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [loading, setLoading] = useState(true);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    async function loadDatasetData() {
      try {
        setLoading(true);
        const [ds, prof, prev] = await Promise.all([
          api.getDataset(datasetId),
          api.getDatasetProfile(datasetId),
          api.previewDataset(datasetId, 1, 25),
        ]);
        setDataset(ds);
        setProfile(prof);
        setPreview(prev);
      } catch (err: any) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadDatasetData();
  }, [datasetId]);

  const handlePageChange = async (newPage: number) => {
    try {
      setPreviewLoading(true);
      const prev = await api.previewDataset(datasetId, newPage, pageSize);
      setPreview(prev);
      setPage(newPage);
    } catch (err) {
      console.error(err);
    } finally {
      setPreviewLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
          <span className="text-xs text-slate-500">Loading dataset profile...</span>
        </div>
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="text-center py-16 saas-card p-8">
        <p className="text-slate-600 font-medium">Dataset not found or access denied.</p>
        <Link href="/dashboard/datasets" className="text-blue-600 mt-2 inline-block text-xs font-semibold">
          Return to Datasets
        </Link>
      </div>
    );
  }

  const totalPages = preview ? Math.ceil(preview.total_rows / pageSize) : 1;

  return (
    <div className="space-y-6">
      {/* Top Header & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2">
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/datasets"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-2xs hover:bg-slate-50 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">{dataset.name}</h1>
              <span className="rounded-md bg-blue-50 border border-blue-100 px-2 py-0.5 text-xs font-mono text-blue-700">
                {dataset.original_filename}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Profiled {dataset.row_count.toLocaleString()} rows • {dataset.column_count} columns • {(dataset.file_size / 1024).toFixed(1)} KB
            </p>
          </div>
        </div>

        <Link
          href={`/dashboard/workspace?dataset=${dataset.id}`}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 active:scale-[0.98] transition-all"
        >
          <Terminal className="h-4 w-4" />
          <span>Launch Analysis Workspace</span>
        </Link>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200">
        <button
          onClick={() => setActiveTab("profile")}
          className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-semibold transition-colors ${
            activeTab === "profile"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <PieChart className="h-4 w-4" />
          <span>Statistical Profile</span>
        </button>
        <button
          onClick={() => setActiveTab("preview")}
          className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-semibold transition-colors ${
            activeTab === "preview"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <TableIcon className="h-4 w-4" />
          <span>Paginated Data Preview</span>
        </button>
      </div>

      {/* TAB 1: DATA PROFILING */}
      {activeTab === "profile" && profile && (
        <div className="space-y-6">
          {/* Summary Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="saas-card p-4">
              <span className="text-[11px] font-semibold uppercase text-slate-400">Total Rows</span>
              <p className="text-xl font-bold text-slate-900 mt-1">{profile.row_count.toLocaleString()}</p>
            </div>
            <div className="saas-card p-4">
              <span className="text-[11px] font-semibold uppercase text-slate-400">Total Columns</span>
              <p className="text-xl font-bold text-slate-900 mt-1">{profile.column_count}</p>
            </div>
            <div className="saas-card p-4">
              <span className="text-[11px] font-semibold uppercase text-slate-400">Duplicate Rows</span>
              <p className="text-xl font-bold text-slate-900 mt-1">{profile.duplicate_rows}</p>
            </div>
            <div className="saas-card p-4">
              <span className="text-[11px] font-semibold uppercase text-slate-400">Memory Usage</span>
              <p className="text-xl font-bold text-slate-900 mt-1">{(profile.memory_usage_bytes / 1024).toFixed(1)} KB</p>
            </div>
          </div>

          {/* Column Profiling Cards */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-slate-900">Column Profiles & Statistical Distributions</h3>
            <div className="grid grid-cols-1 gap-4">
              {profile.columns.map((col) => (
                <div key={col.name} className="saas-card p-5 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs font-bold text-slate-900">{col.name}</span>
                      <span className="saas-badge bg-blue-50 text-blue-700 text-[10px] uppercase font-mono">
                        {col.inferred_type}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      <span>Unique values: <strong className="text-slate-800">{col.unique_count.toLocaleString()}</strong></span>
                      <span>Missing: <strong className="text-slate-800">{col.null_count} ({col.null_percentage}%)</strong></span>
                    </div>
                  </div>

                  {/* Null Percentage Completeness Bar */}
                  <div>
                    <div className="flex justify-between text-[11px] text-slate-500 mb-1">
                      <span>Data Completeness</span>
                      <span className="font-semibold text-slate-700">{(100 - col.null_percentage).toFixed(1)}% Present</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full"
                        style={{ width: `${100 - col.null_percentage}%` }}
                      />
                    </div>
                  </div>

                  {/* Numeric Statistics Grid */}
                  {(col.inferred_type === "integer" || col.inferred_type === "float") && col.mean !== null && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2 rounded-lg bg-slate-50 p-3 text-center border border-slate-100">
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase font-semibold block">Mean</span>
                        <span className="text-xs font-bold text-slate-800">{col.mean?.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase font-semibold block">Std Dev</span>
                        <span className="text-xs font-bold text-slate-800">{col.std?.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase font-semibold block">Min</span>
                        <span className="text-xs font-bold text-slate-800">{col.min}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase font-semibold block">25% (Q1)</span>
                        <span className="text-xs font-bold text-slate-800">{col.q25}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase font-semibold block">Median</span>
                        <span className="text-xs font-bold text-blue-600">{col.median}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase font-semibold block">75% (Q3)</span>
                        <span className="text-xs font-bold text-slate-800">{col.q75}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase font-semibold block">Max</span>
                        <span className="text-xs font-bold text-slate-800">{col.max}</span>
                      </div>
                    </div>
                  )}

                  {/* Categorical Top Values */}
                  {col.top_values && col.top_values.length > 0 && (
                    <div>
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                        Frequent Values
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {col.top_values.map((item, idx) => (
                          <div
                            key={idx}
                            className="flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700"
                          >
                            <span className="font-medium text-slate-800">{item.value}</span>
                            <span className="rounded bg-white border border-slate-200 px-1 text-[10px] text-blue-600 font-mono">
                              {item.count}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: DATA PREVIEW */}
      {activeTab === "preview" && preview && (
        <div className="saas-card p-6 space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>
              Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, preview.total_rows)} of {preview.total_rows.toLocaleString()} rows
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1 || previewLoading}
                onClick={() => handlePageChange(page - 1)}
                className="flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                <span>Prev</span>
              </button>
              <span className="font-mono text-xs text-slate-700 px-1">
                {page} / {totalPages}
              </span>
              <button
                disabled={page >= totalPages || previewLoading}
                onClick={() => handlePageChange(page + 1)}
                className="flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
              >
                <span>Next</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-left text-xs text-slate-800">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase text-[11px]">
                <tr>
                  <th className="px-4 py-2.5 w-12 text-slate-400">#</th>
                  {preview.columns.map((c) => (
                    <th key={c} className="px-4 py-2.5 text-slate-700">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {preview.rows.map((row, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-4 py-2 text-slate-400">{(page - 1) * pageSize + idx + 1}</td>
                    {preview.columns.map((col) => (
                      <td key={col} className="px-4 py-2 whitespace-nowrap text-slate-800">
                        {row[col] !== null && row[col] !== undefined ? String(row[col]) : "null"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

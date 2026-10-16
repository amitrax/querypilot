"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { DatasetSummary } from "@/types";
import {
  Database,
  UploadCloud,
  Trash2,
  FileSpreadsheet,
  ArrowRight,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Table,
  BarChart2,
  Plus,
} from "lucide-react";

const SAMPLE_SALES_CSV = `product,category,revenue,units_sold,region,date
MacBook Pro,Electronics,2400.00,8,North,2026-01-15
iPhone 16,Electronics,1200.00,20,North,2026-01-16
Standing Desk,Furniture,650.00,12,South,2026-01-18
Ergonomic Chair,Furniture,350.00,25,South,2026-01-19
Sony WH-1000XM5,Electronics,399.00,15,East,2026-01-20
Espresso Machine,Appliances,850.00,6,East,2026-01-21
Air Fryer,Appliances,150.00,18,West,2026-01-22
Smart Watch,Electronics,299.00,30,West,2026-01-23
Monitor 4K,Electronics,550.00,14,North,2026-01-24
Mechanical Keyboard,Electronics,120.00,45,East,2026-01-25
`;

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDatasets = async () => {
    try {
      setLoading(true);
      const data = await api.getDatasets();
      setDatasets(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDatasets();
  }, []);

  const handleFileUpload = async (file: File) => {
    if (!file.name.endsWith(".csv")) {
      setUploadError("Only CSV files (.csv) are supported.");
      return;
    }
    setUploadError(null);
    setUploadSuccess(null);
    setUploading(true);

    try {
      const newDataset = await api.uploadDataset(file);
      setUploadSuccess(
        `Successfully uploaded and profiled "${newDataset.name}" (${newDataset.row_count} rows, ${newDataset.column_count} columns).`
      );
      await loadDatasets();
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload dataset.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleUploadSample = async () => {
    const blob = new Blob([SAMPLE_SALES_CSV], { type: "text/csv" });
    const file = new File([blob], "sample_enterprise_sales.csv", { type: "text/csv" });
    await handleFileUpload(file);
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete dataset "${name}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await api.deleteDataset(id);
      setDatasets(datasets.filter((d) => d.id !== id));
    } catch (err: any) {
      alert(err.message || "Failed to delete dataset.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header and Action Area */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Datasets Library</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage your uploaded CSV datasets, inspect column profiling, and launch analytics.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleUploadSample}
            disabled={uploading}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 hover:text-slate-900 transition-colors disabled:opacity-50"
          >
            <Sparkles className="h-3.5 w-3.5 text-blue-600" />
            <span>Load Sample Data</span>
          </button>

          <label className="flex items-center gap-1.5 cursor-pointer rounded-lg bg-blue-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 active:scale-[0.98] transition-all">
            <UploadCloud className="h-4 w-4" />
            <span>{uploading ? "Profiling..." : "Upload CSV"}</span>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              className="hidden"
              disabled={uploading}
              onChange={(e) => {
                if (e.target.files?.[0]) {
                  handleFileUpload(e.target.files[0]);
                }
              }}
            />
          </label>
        </div>
      </div>

      {/* Notifications */}
      {uploadError && (
        <div className="flex items-center gap-2.5 rounded-lg border border-red-200 bg-red-50 p-4 text-xs text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
          <span>{uploadError}</span>
        </div>
      )}

      {uploadSuccess && (
        <div className="flex items-center gap-2.5 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-800">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
          <span>{uploadSuccess}</span>
        </div>
      )}

      {/* Upload Drag & Drop Box */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (e.dataTransfer.files?.[0]) {
            handleFileUpload(e.dataTransfer.files[0]);
          }
        }}
        className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 bg-white p-8 text-center hover:border-blue-400 hover:bg-blue-50/20 transition-all shadow-2xs"
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600 mb-3">
          <UploadCloud className="h-6 w-6" />
        </div>
        <h3 className="text-xs font-bold text-slate-900">Drag and drop your CSV file here</h3>
        <p className="text-[11px] text-slate-500 mt-1 max-w-sm">
          Strict schema validation, formula injection sanitization, and automatic statistical profiling (Max size: 25 MB).
        </p>
      </div>

      {/* Datasets Grid */}
      {loading ? (
        <div className="flex min-h-[30vh] items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
            <span className="text-xs text-slate-500">Loading datasets...</span>
          </div>
        </div>
      ) : datasets.length === 0 ? (
        <div className="saas-card p-12 text-center">
          <Database className="mx-auto h-12 w-12 text-slate-300 mb-3" />
          <h3 className="text-sm font-semibold text-slate-800">No datasets found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
            Upload your first CSV file or click &quot;Load Sample Data&quot; to begin exploring.
          </p>
          <button
            onClick={handleUploadSample}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 transition-colors"
          >
            <Sparkles className="h-4 w-4" />
            <span>Load Enterprise Sample Data</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {datasets.map((d) => (
            <div key={d.id} className="saas-card p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                      <FileSpreadsheet className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 tracking-tight">{d.name}</h3>
                      <span className="text-[11px] text-slate-400 font-mono truncate block max-w-[160px]">
                        {d.original_filename}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(d.id, d.name)}
                    title="Delete dataset"
                    className="text-slate-400 hover:text-red-500 transition-colors p-1"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-2 py-3 border-y border-slate-100 text-center my-3">
                  <div>
                    <span className="text-[10px] uppercase font-semibold text-slate-400 block">Rows</span>
                    <span className="text-xs font-bold text-slate-800">{d.row_count.toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-semibold text-slate-400 block">Columns</span>
                    <span className="text-xs font-bold text-slate-800">{d.column_count}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-semibold text-slate-400 block">Size</span>
                    <span className="text-xs font-bold text-slate-800">{(d.file_size / 1024).toFixed(1)} KB</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <Link
                  href={`/dashboard/datasets/${d.id}`}
                  className="flex-1 text-center rounded-lg border border-slate-200 bg-white py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 hover:text-slate-900 transition-colors"
                >
                  Profile & Preview
                </Link>
                <Link
                  href={`/dashboard/workspace?dataset=${d.id}`}
                  className="flex items-center justify-center gap-1 rounded-lg bg-blue-50 border border-blue-200 px-3 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-100 transition-colors"
                >
                  <span>Query</span>
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

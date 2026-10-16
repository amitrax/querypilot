"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { AnalysisResponse } from "@/types";
import {
  History,
  Terminal,
  Trash2,
  Clock,
  ArrowRight,
  ShieldCheck,
  BarChart2,
} from "lucide-react";
import { FormattedText } from "@/components/FormattedText";

export default function HistoryPage() {
  const [analyses, setAnalyses] = useState<AnalysisResponse[]>([]);
  const [loading, setLoading] = useState(true);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const data = await api.getAnalyses();
      setAnalyses(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this saved analysis?")) return;
    try {
      await api.deleteAnalysis(id);
      setAnalyses(analyses.filter((a) => a.id !== id));
    } catch (err: any) {
      alert(err.message || "Failed to delete analysis.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="pb-2">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Saved Analyses & History</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Review all computational queries, execution timings, and findings generated across datasets.
        </p>
      </div>

      {loading ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
            <span className="text-xs text-slate-500">Loading analysis history...</span>
          </div>
        </div>
      ) : analyses.length === 0 ? (
        <div className="saas-card p-12 text-center">
          <History className="mx-auto h-12 w-12 text-slate-300 mb-3" />
          <h3 className="text-sm font-semibold text-slate-800">No analyses history found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
            Ask questions in the analysis workspace to save analytical results here.
          </p>
          <Link
            href="/dashboard/workspace"
            className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 transition-colors"
          >
            <span>Go to Analysis Workspace</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {analyses.map((item) => (
            <div key={item.id} className="saas-card p-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3 mb-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                    <Terminal className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-slate-900">{item.question}</h3>
                    <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5">
                      <span className="saas-badge bg-emerald-50 text-emerald-700 text-[10px] py-0 px-1.5">
                        {item.status}
                      </span>
                      <span>•</span>
                      <span>
                        Execution: <strong className="font-mono text-slate-700">{item.result?.execution_time_ms ? `${item.result.execution_time_ms} ms` : "Verified"}</strong>
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Link
                    href={`/dashboard/workspace?dataset=${item.dataset_id}&q=${encodeURIComponent(item.question)}`}
                    className="flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                  >
                    <span>Reopen</span>
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="p-1.5 text-slate-400 hover:text-red-500 rounded transition-colors"
                    title="Delete analysis"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {item.explanation && (
                <div className="text-xs text-slate-700 leading-relaxed font-medium mb-3">
                  <FormattedText text={item.explanation} />
                </div>
              )}

              <div className="flex items-center justify-between pt-2 text-[11px] text-slate-400 border-t border-slate-100">
                <span>
                  Operation: <strong className="text-slate-600 uppercase font-mono">{item.analysis_plan?.operation || "Query"}</strong>
                </span>
                <span>{new Date(item.created_at).toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

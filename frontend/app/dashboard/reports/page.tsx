"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Report } from "@/types";
import {
  FileSpreadsheet,
  Download,
  Calendar,
  CheckCircle2,
  Clock,
  Sparkles,
  ShieldCheck,
} from "lucide-react";

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadReports() {
      try {
        setLoading(true);
        const data = await api.getReports();
        setReports(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadReports();
  }, []);

  return (
    <div className="space-y-6">
      <div className="pb-2">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Reports & Exports</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Download formula-sanitized CSV exports generated from your analysis sessions.
        </p>
      </div>

      {loading ? (
        <div className="flex min-h-[40vh] items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
            <span className="text-xs text-slate-500">Loading reports...</span>
          </div>
        </div>
      ) : reports.length === 0 ? (
        <div className="saas-card p-12 text-center">
          <FileSpreadsheet className="mx-auto h-12 w-12 text-slate-300 mb-3" />
          <h3 className="text-sm font-semibold text-slate-800">No reports generated yet</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
            Run an analysis in the workspace and click &quot;Export CSV&quot; to generate downloadable reports.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {reports.map((r) => (
            <div key={r.id} className="saas-card p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                      <FileSpreadsheet className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase font-mono">
                        {r.format} Report
                      </h3>
                      <span className="text-[11px] text-slate-400 font-mono">
                        ID: {r.id.slice(0, 8)}
                      </span>
                    </div>
                  </div>
                  <span className="saas-badge bg-emerald-50 text-emerald-700 text-[10px] capitalize">
                    {r.status}
                  </span>
                </div>

                <div className="rounded-lg bg-slate-50 p-3 border border-slate-100 text-xs text-slate-700 space-y-1.5 my-4">
                  <div className="flex justify-between">
                    <span className="text-slate-400 text-[11px]">Security</span>
                    <span className="text-emerald-700 font-semibold text-[11px] flex items-center gap-1">
                      <ShieldCheck className="h-3 w-3" />
                      Formula Injection Defense
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400 text-[11px]">Created</span>
                    <span className="text-slate-700 text-[11px]">{new Date(r.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>

              <a
                href={api.getReportDownloadUrl(r.id)}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 active:scale-[0.98] transition-all"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Download {r.format.toUpperCase()}</span>
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

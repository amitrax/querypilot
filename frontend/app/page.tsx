import React from "react";
import Link from "next/link";
import {
  Sparkles,
  Database,
  BarChart3,
  ShieldCheck,
  Cpu,
  ArrowRight,
  FileCheck2,
  Table,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="relative min-h-screen bg-slate-50 text-slate-900 selection:bg-blue-600 selection:text-white">
      {/* Navigation Header */}
      <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200/80 bg-white/95 px-6 sm:px-8 backdrop-blur-md max-w-7xl mx-auto">
        <div className="flex items-center gap-2.5 font-bold tracking-tight text-slate-900">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white shadow-xs">
            <Sparkles className="h-4 w-4" />
          </div>
          <span className="text-lg font-bold">
            Query<span className="text-blue-600">Pilot</span>
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="rounded-lg px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 transition-colors"
          >
            Sign In
          </Link>
          <Link
            href="/register"
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 active:scale-[0.98] transition-all"
          >
            <span>Get Started</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <main className="mx-auto max-w-5xl px-6 pt-16 pb-20 text-center">
        <div className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 mb-6">
          <Cpu className="h-3.5 w-3.5" />
          <span>Deterministic AI Data Analyst • Zero Hallucinations</span>
        </div>

        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 leading-[1.15] max-w-3xl mx-auto">
          AI-Powered Data Analyst Workspace for Real Computations
        </h1>

        <p className="mt-4 text-sm sm:text-base text-slate-600 max-w-2xl mx-auto leading-relaxed">
          Upload any CSV, explore automatic column profiling, and ask questions in natural language.
          QueryPilot compiles safe analytical plans and executes them strictly in verified pandas operations.
        </p>

        {/* CTA buttons */}
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/register"
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 active:scale-[0.98] transition-all"
          >
            <span>Start Free Workspace</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/login"
            className="rounded-lg border border-slate-200 bg-white px-5 py-2.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 hover:text-slate-900 transition-all"
          >
            Sign In with Test Account
          </Link>
        </div>

        {/* Interactive Workspace Preview Mockup Card */}
        <div className="mt-12 saas-card p-5 sm:p-6 text-left shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
            <div className="flex items-center gap-2">
              <span className="flex h-2.5 w-2.5 rounded-full bg-slate-300" />
              <span className="flex h-2.5 w-2.5 rounded-full bg-slate-300" />
              <span className="flex h-2.5 w-2.5 rounded-full bg-slate-300" />
              <span className="ml-2 text-xs font-mono text-slate-500">querypilot / workspace / enterprise_sales.csv</span>
            </div>
            <div className="saas-badge bg-emerald-50 text-emerald-700 border border-emerald-100 text-[11px]">
              Deterministic Plan Verified
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2 rounded-lg border border-slate-100 bg-slate-50 p-4">
              <div className="flex items-center justify-between text-xs text-slate-600 mb-2">
                <span className="font-semibold text-slate-800">Q: &quot;Which products generated the highest revenue?&quot;</span>
                <span className="text-blue-600 font-mono text-[11px]">1.82 ms execution</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Based on verified computation across the dataset, <strong>Laptop</strong> ranks first with a sum of <strong>$20,400.00</strong> for revenue, followed by Phone ($18,300.00).
              </p>
            </div>

            <div className="rounded-lg border border-slate-100 bg-slate-50 p-4 flex flex-col justify-between">
              <div>
                <span className="text-[10px] font-semibold uppercase text-slate-400 block mb-1">Execution Engine</span>
                <span className="text-xs font-bold text-slate-800">pandas 2.x Whitelist</span>
              </div>
              <div className="mt-3 pt-3 border-t border-slate-200/60">
                <span className="text-[10px] font-semibold uppercase text-slate-400 block mb-1">DDE Formula Defense</span>
                <span className="text-xs font-bold text-emerald-700">Protected</span>
              </div>
            </div>
          </div>
        </div>

        {/* Features Grid */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          <div className="saas-card p-5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600 mb-3">
              <Database className="h-4 w-4" />
            </div>
            <h3 className="text-xs font-bold text-slate-900">Instant CSV Profiling</h3>
            <p className="mt-1.5 text-xs text-slate-500 leading-relaxed">
              Upload any CSV to automatically calculate data completeness, null rates, and distribution percentiles.
            </p>
          </div>

          <div className="saas-card p-5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600 mb-3">
              <BarChart3 className="h-4 w-4" />
            </div>
            <h3 className="text-xs font-bold text-slate-900">Recharts Visualizations</h3>
            <p className="mt-1.5 text-xs text-slate-500 leading-relaxed">
              Natural-language questions automatically map to interactive Bar, Line, and Pie charts without hallucinations.
            </p>
          </div>

          <div className="saas-card p-5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-50 text-purple-600 mb-3">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <h3 className="text-xs font-bold text-slate-900">Enterprise Security</h3>
            <p className="mt-1.5 text-xs text-slate-500 leading-relaxed">
              Strict multi-tenant row isolation, Argon2id passwords, and formula injection sanitization on all exports.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

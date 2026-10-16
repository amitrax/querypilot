"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Database,
  Terminal,
  History,
  FileSpreadsheet,
  Settings,
  PlusCircle,
  HelpCircle,
  Sparkles,
  ChevronRight,
  ShieldCheck,
} from "lucide-react";

interface SidebarProps {
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export function Sidebar({ mobileOpen, onCloseMobile }: SidebarProps) {
  const pathname = usePathname();

  const navItems = [
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "Datasets", href: "/dashboard/datasets", icon: Database },
    { label: "Analysis Workspace", href: "/dashboard/workspace", icon: Terminal },
    { label: "Saved Analyses", href: "/dashboard/history", icon: History },
    { label: "Reports", href: "/dashboard/reports", icon: FileSpreadsheet },
    { label: "Settings", href: "/dashboard/settings", icon: Settings },
  ];

  const sidebarContent = (
    <div className="flex h-full flex-col justify-between p-4">
      <div className="space-y-6">
        {/* Quick action button: New Analysis */}
        <div className="px-1 pt-1">
          <Link
            href="/dashboard/workspace"
            onClick={onCloseMobile}
            className="flex items-center justify-center gap-2 w-full rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 active:scale-[0.98] transition-all"
          >
            <PlusCircle className="h-4 w-4" />
            <span>New Analysis</span>
          </Link>
        </div>

        {/* Navigation list */}
        <div className="space-y-1">
          <div className="px-3 pb-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
            Workspace
          </div>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href));
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onCloseMobile}
                  className={`flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium transition-all ${
                    isActive
                      ? "bg-blue-50 text-blue-700 font-semibold shadow-xs"
                      : "text-slate-600 hover:bg-slate-100/70 hover:text-slate-900"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon
                      className={`h-4 w-4 ${
                        isActive ? "text-blue-600" : "text-slate-400"
                      }`}
                    />
                    <span>{item.label}</span>
                  </div>
                  {isActive && (
                    <div className="h-1.5 w-1.5 rounded-full bg-blue-600" />
                  )}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Footer / Info Card */}
      <div className="rounded-xl border border-slate-200/90 bg-slate-50/70 p-3.5 text-xs text-slate-600">
        <div className="flex items-center gap-2 font-semibold text-slate-800 mb-1">
          <ShieldCheck className="h-4 w-4 text-emerald-600" />
          <span className="text-[11px]">Deterministic Engine</span>
        </div>
        <p className="text-[11px] leading-relaxed text-slate-500">
          Powered strictly by verified pandas operations. Zero hallucinations, 100% reproducible metrics.
        </p>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop fixed sidebar */}
      <aside className="hidden lg:flex w-64 flex-col border-r border-slate-200/80 bg-white">
        {sidebarContent}
      </aside>

      {/* Mobile drawer overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
            onClick={onCloseMobile}
          />
          {/* Drawer content */}
          <div className="fixed inset-y-0 left-0 w-64 bg-white shadow-xl flex flex-col z-50">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}

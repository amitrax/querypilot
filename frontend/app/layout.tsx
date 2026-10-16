import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "QueryPilot — AI Data Analyst Workspace",
  description: "Enterprise AI-powered data analyst workspace. Upload CSVs, profile datasets, perform deterministic analytics, and generate real-time reports.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0b0f19] text-slate-100 antialiased selection:bg-blue-600 selection:text-white">
        {children}
      </body>
    </html>
  );
}

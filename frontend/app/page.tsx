"use client";
import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  FileSpreadsheet,
  Layers,
  Quote,
  ShieldCheck,
  Sparkles,
  FileText,
  CheckCircle2,
} from "lucide-react";
import { isAuthenticated } from "@/lib/api";
import { Logo } from "@/components/Logo";

const FEATURES = [
  {
    icon: Layers,
    title: "Hybrid RAG Retrieval",
    desc: "Combines semantic vector search with BM25 keyword matching and cross-encoder reranking for exact financial figures.",
  },
  {
    icon: FileSpreadsheet,
    title: "Tables, Charts & Scans",
    desc: "Extracts multi-column text, financial tables, embedded charts, and scanned pages via OCR + Vision AI.",
  },
  {
    icon: Quote,
    title: "Page-Level Citations",
    desc: "Every answer is grounded in your uploaded PDFs with confidence scoring and exact page references.",
  },
];

export default function LandingPage() {
  const router = useRouter();
  useEffect(() => {
    if (isAuthenticated()) router.replace("/dashboard");
  }, [router]);

  return (
    <main className="min-h-screen flex flex-col bg-[#07080d] bg-grid relative overflow-hidden">
      {/* Ambient top glow */}
      <div
        className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 w-[780px] h-[420px] rounded-full opacity-25 blur-3xl"
        style={{
          background:
            "radial-gradient(circle, rgba(99,102,241,0.55) 0%, rgba(139,92,246,0.18) 50%, transparent 75%)",
        }}
      />

      {/* Sticky Glass Navbar */}
      <header className="sticky top-0 z-20 backdrop-blur-md bg-[#07080d]/75 border-b border-white/[0.07]">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-6 py-4">
          <Logo />
          <div className="flex items-center gap-3">
            <Link
              href="/auth/signin"
              className="px-4 py-2 text-sm text-slate-400 hover:text-slate-100 transition-colors"
            >
              Sign in
            </Link>
            <Link
              href="/auth/signup"
              className="px-4 py-2 text-sm font-medium rounded-lg bg-indigo-500 hover:bg-indigo-400 text-white shadow-lg shadow-indigo-500/20 transition-all"
            >
              Get started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 pt-20 pb-16 text-center flex flex-col items-center">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-medium border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 mb-6">
          <Sparkles className="w-3.5 h-3.5" />
          Financial Document Intelligence
        </div>

        <h1 className="text-4xl sm:text-6xl font-bold tracking-tight text-slate-50 leading-[1.1] max-w-3xl">
          Interrogate financial PDFs{" "}
          <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-emerald-400 bg-clip-text text-transparent">
            with verified citations
          </span>
        </h1>

        <p className="mt-5 text-base sm:text-lg text-slate-400 max-w-2xl leading-relaxed">
          Upload balance sheets, quarterly filings, or invoices. Ask complex
          questions in plain English and get auditable answers backed by exact
          page numbers.
        </p>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/auth/signup"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium bg-indigo-500 hover:bg-indigo-400 text-white shadow-xl shadow-indigo-500/25 transition-all"
          >
            Start analyzing free
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/auth/signin"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium border border-white/10 bg-white/[0.03] hover:bg-white/[0.06] text-slate-200 transition-colors"
          >
            Sign in to workspace
          </Link>
        </div>

        {/* Product Preview Mockup */}
        <div className="mt-14 w-full max-w-4xl rounded-2xl border border-white/10 bg-[#0e1017]/90 shadow-2xl shadow-black/60 overflow-hidden text-left">
          {/* Window chrome */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.07] bg-white/[0.02]">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-white/15" />
              <span className="w-2.5 h-2.5 rounded-full bg-white/15" />
              <span className="w-2.5 h-2.5 rounded-full bg-white/15" />
            </div>
            <span className="text-xs font-mono-code text-slate-500">
              ledgerlens.app/chat
            </span>
            <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400">
              <ShieldCheck className="w-3.5 h-3.5" /> Grounded
            </span>
          </div>

          <div className="grid sm:grid-cols-5 divide-y sm:divide-y-0 sm:divide-x divide-white/[0.07]">
            {/* Sidebar mock */}
            <div className="sm:col-span-2 p-4 space-y-2.5 bg-white/[0.01]">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Active Documents
              </p>
              <div className="flex items-center justify-between px-3 py-2.5 rounded-lg border border-indigo-500/40 bg-indigo-500/10">
                <div className="flex items-center gap-2 min-w-0">
                  <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                  <span className="text-xs font-medium text-slate-100 truncate">
                    FY25_Annual_Report.pdf
                  </span>
                </div>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              </div>
              <div className="flex items-center justify-between px-3 py-2.5 rounded-lg border border-white/[0.06] bg-white/[0.02]">
                <div className="flex items-center gap-2 min-w-0">
                  <FileText className="w-4 h-4 text-slate-500 shrink-0" />
                  <span className="text-xs text-slate-400 truncate">
                    Q4_Balance_Sheet.pdf
                  </span>
                </div>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400/60 shrink-0" />
              </div>
            </div>

            {/* Q&A mock */}
            <div className="sm:col-span-3 p-5 space-y-4">
              <div className="flex justify-end">
                <div className="px-3.5 py-2 rounded-2xl rounded-br-sm bg-indigo-500 text-white text-xs sm:text-sm max-w-xs">
                  What was the YoY operating margin expansion in Q4?
                </div>
              </div>

              <div className="space-y-2.5">
                <div className="p-3.5 rounded-2xl rounded-bl-sm bg-[#141722] border border-white/[0.07] text-xs sm:text-sm text-slate-200 leading-relaxed">
                  Operating margin expanded by{" "}
                  <span className="font-mono-code text-emerald-400 font-medium">
                    +320 bps
                  </span>{" "}
                  YoY, rising from 18.4% to{" "}
                  <span className="font-mono-code text-slate-100 font-medium">
                    21.6%
                  </span>{" "}
                  driven by cloud infrastructure optimization.
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Confidence: HIGH
                  </span>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono-code bg-white/[0.04] text-slate-400 border border-white/[0.07]">
                    p.14 · Condensed Income Statement
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Bento */}
      <section className="relative z-10 max-w-5xl mx-auto w-full px-6 pb-20">
        <div className="grid sm:grid-cols-3 gap-4">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="p-6 rounded-2xl border border-white/[0.07] bg-[#0e1017]/80 hover:border-white/15 transition-colors"
            >
              <div className="w-9 h-9 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-4">
                <Icon className="w-4 h-4 text-indigo-400" />
              </div>
              <h3 className="text-sm font-semibold text-slate-100 mb-1.5">
                {title}
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="mt-auto border-t border-white/[0.06] py-6 text-center text-xs text-slate-500">
        Built by Vansh Maheshwari · LedgerLens 2026
      </footer>
    </main>
  );
}

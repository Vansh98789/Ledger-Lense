"use client";
import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  UploadCloud,
  FileText,
  MessageSquare,
  LogOut,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
  ArrowUpRight,
} from "lucide-react";
import {
  isAuthenticated,
  listDocuments,
  uploadDocument,
  signout,
  type Document,
} from "@/lib/api";
import { Logo } from "@/components/Logo";

const STATUS_META: Record<
  Document["status"],
  { label: string; badge: string; dot: string }
> = {
  QUEUED: {
    label: "Queued",
    badge: "bg-amber-500/10 text-amber-300 border-amber-500/20",
    dot: "bg-amber-400 animate-pulse",
  },
  EXTRACTING: {
    label: "EXTRACTING",
    badge: "bg-indigo-500/10 text-indigo-300 border-indigo-500/20",
    dot: "bg-indigo-400 animate-pulse",
  },
  COMPLETED: {
    label: "Ready",
    badge: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
    dot: "bg-emerald-400",
  },
  FAILED: {
    label: "Failed",
    badge: "bg-red-500/10 text-red-300 border-red-500/20",
    dot: "bg-red-400",
  },
};

export default function DashboardPage() {
  const router = useRouter();
  const [docs, setDocs] = useState<Document[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/auth/signin");
      return;
    }
    fetchDocs().finally(() => setInitialLoading(false));
  }, [router]);

  // Poll in-progress docs
  useEffect(() => {
    const pending = docs.filter(
      (d) => d.status === "QUEUED" || d.status === "EXTRACTING",
    );
    if (!pending.length) return;
    const id = setTimeout(fetchDocs, 2000);
    return () => clearTimeout(id);
  }, [docs]);

  async function fetchDocs() {
    try {
      const data = await listDocuments();
      setDocs(data);
    } catch {
      /* ignore transient poll error */
    }
  }

  async function handleUpload(file: File) {
    setError("");
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }
    setUploading(true);
    try {
      await uploadDocument(file);
      await fetchDocs();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
    e.target.value = "";
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  }

  function handleSignout() {
    signout();
    router.push("/");
  }

  const readyCount = docs.filter((d) => d.status === "COMPLETED").length;
  const activeCount = docs.filter(
    (d) => d.status === "QUEUED" || d.status === "EXTRACTING",
  ).length;

  return (
    <div className="min-h-screen flex flex-col bg-[#07080d]">
      {/* Top Navbar */}
      <header className="sticky top-0 z-20 backdrop-blur-md bg-[#07080d]/80 border-b border-white/[0.07]">
        <div className="max-w-5xl mx-auto flex items-center justify-between px-6 py-3.5">
          <Logo href="/dashboard" />
          <div className="flex items-center gap-3">
            <Link
              href="/chat"
              className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-medium px-3.5 py-2 rounded-lg border border-white/10 bg-white/[0.03] hover:bg-white/[0.07] text-slate-200 transition-colors"
            >
              <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
              Open Chat
            </Link>
            <button
              onClick={handleSignout}
              className="inline-flex items-center gap-1.5 text-xs sm:text-sm px-3 py-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] transition-colors cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-10 flex flex-col gap-8">
        {/* Header + Quick Stats */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-50">
              Document Workspace
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Upload financial PDFs to extract tables, charts, and text for AI
              Q&amp;A.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <div className="px-3 py-1.5 rounded-lg border border-white/[0.07] bg-[#0e1017] text-xs text-slate-400">
              Total:{" "}
              <span className="font-mono-code text-slate-100 font-medium">
                {docs.length}
              </span>
            </div>
            <div className="px-3 py-1.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5 text-xs text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span className="font-mono-code font-medium">
                {readyCount}
              </span>{" "}
              ready
            </div>
            {activeCount > 0 && (
              <div className="px-3 py-1.5 rounded-lg border border-indigo-500/20 bg-indigo-500/5 text-xs text-indigo-300 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 animate-pulse" />
                <span className="font-mono-code font-medium">
                  {activeCount}
                </span>{" "}
                indexing
              </div>
            )}
          </div>
        </div>

        {/* Drop zone */}
        <div
          onDrop={onDrop}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onClick={() => !uploading && fileRef.current?.click()}
          className={`group relative rounded-2xl border-2 border-dashed p-10 flex flex-col items-center justify-center gap-3 cursor-pointer transition-all ${
            dragging
              ? "border-indigo-400 bg-indigo-500/10"
              : "border-white/10 bg-[#0e1017]/60 hover:border-indigo-500/50 hover:bg-[#0e1017]"
          }`}
        >
          <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center group-hover:scale-105 transition-transform">
            {uploading ? (
              <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
            ) : (
              <UploadCloud className="w-5 h-5 text-indigo-400" />
            )}
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-slate-200">
              {uploading
                ? "Uploading & queuing ingestion…"
                : "Drop a PDF here, or click to browse"}
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Supports multi-column reports, tables, and scanned PDFs · Max 25
              MB
            </p>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={onFileChange}
          />
        </div>

        {error && (
          <div className="flex items-center gap-2 px-4 py-3 rounded-xl text-xs bg-red-500/10 border border-red-500/20 text-red-400">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Document List */}
        <section className="flex flex-col gap-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Your Documents
          </h2>

          {initialLoading ? (
            <div className="flex flex-col gap-2.5">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-16 rounded-xl border border-white/[0.06] bg-[#0e1017] animate-pulse"
                />
              ))}
            </div>
          ) : docs.length === 0 ? (
            <div className="rounded-2xl border border-white/[0.06] bg-[#0e1017]/50 py-14 text-center">
              <FileText className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-sm text-slate-400">
                No documents uploaded yet
              </p>
              <p className="text-xs text-slate-600 mt-1">
                Upload your first financial PDF above to begin.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-2.5">
              {docs.map((doc) => {
                const meta = STATUS_META[doc.status] ?? STATUS_META.QUEUED;
                return (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between gap-4 p-4 rounded-xl border border-white/[0.07] bg-[#0e1017] hover:border-white/15 transition-colors"
                  >
                    <div className="flex items-center gap-3.5 min-w-0">
                      <div className="w-9 h-9 rounded-lg bg-white/[0.04] border border-white/[0.07] flex items-center justify-center shrink-0">
                        <FileText className="w-4 h-4 text-indigo-400" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-100 truncate">
                          {doc.filename}
                        </p>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Uploaded{" "}
                          {new Date(doc.created_at).toLocaleDateString(
                            undefined,
                            {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                            },
                          )}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <span
                        className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border ${meta.badge}`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${meta.dot}`}
                        />
                        {meta.label}
                      </span>

                      {doc.status === "COMPLETED" && (
                        <Link
                          href={`/chat?doc=${doc.id}`}
                          className="inline-flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded-lg bg-indigo-500 hover:bg-indigo-400 text-white transition-colors"
                        >
                          Ask AI
                          <ArrowUpRight className="w-3.5 h-3.5" />
                        </Link>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

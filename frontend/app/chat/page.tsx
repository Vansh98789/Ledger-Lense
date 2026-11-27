"use client";
import { useEffect, useState, useRef, FormEvent, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Send,
  FileText,
  ArrowLeft,
  LogOut,
  Sparkles,
  Check,
  Quote,
  Loader2,
  Bot,
} from "lucide-react";
import {
  isAuthenticated,
  listDocuments,
  chat,
  signout,
  type Document,
  type Citation,
} from "@/lib/api";
import { Logo } from "@/components/Logo";

interface Message {
  role: "user" | "assistant";
  text: string;
  confidence?: string;
  citations?: Citation[];
}

const SAMPLE_PROMPTS = [
  "What was the total revenue and YoY growth?",
  "Summarize the main financial risks mentioned.",
  "What are the operating expenses and net income?",
];

const CONFIDENCE_STYLE: Record<string, string> = {
  HIGH: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  MEDIUM: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  LOW: "bg-red-500/10 text-red-400 border-red-500/20",
};

function ChatApp() {
  const router = useRouter();
  const params = useSearchParams();
  const preselectedDoc = params.get("doc");

  const [docs, setDocs] = useState<Document[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/auth/signin");
      return;
    }
    listDocuments().then((data) => {
      const completed = data.filter((d) => d.status === "COMPLETED");
      setDocs(completed);
      if (preselectedDoc && completed.find((d) => d.id === preselectedDoc)) {
        setSelectedDocs([preselectedDoc]);
      } else if (completed.length === 1) {
        setSelectedDocs([completed[0].id]);
      }
    });
  }, [router, preselectedDoc]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function toggleDoc(id: string) {
    setSelectedDocs((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  async function sendQuestion(q: string) {
    if (!q.trim() || !selectedDocs.length || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setLoading(true);
    try {
      const res = await chat(q, selectedDocs);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: res.answer,
          confidence: res.confidence,
          citations: res.citations,
        },
      ]);
    } catch (err: unknown) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: err instanceof Error ? err.message : "Something went wrong.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleSend(e: FormEvent) {
    e.preventDefault();
    sendQuestion(input.trim());
  }

  return (
    <div className="h-screen flex flex-col bg-[#07080d]">
      {/* Navbar */}
      <header className="shrink-0 backdrop-blur-md bg-[#07080d]/85 border-b border-white/[0.07]">
        <div className="px-6 py-3.5 flex items-center justify-between">
          <Logo href="/dashboard" />
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 text-xs sm:text-sm px-3 py-1.5 rounded-lg border border-white/10 bg-white/[0.03] hover:bg-white/[0.07] text-slate-300 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Documents
            </Link>
            <button
              onClick={() => {
                signout();
                router.push("/");
              }}
              className="inline-flex items-center gap-1.5 text-xs sm:text-sm px-3 py-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] transition-colors cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              Sign out
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar — Document Scope */}
        <aside className="w-64 shrink-0 border-r border-white/[0.07] bg-[#0b0d14] flex flex-col p-4 gap-3 overflow-y-auto">
          <div className="flex items-center justify-between">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Document Scope
            </p>
            <span className="text-[11px] font-mono-code text-slate-500">
              {selectedDocs.length}/{docs.length}
            </span>
          </div>

          {docs.length === 0 ? (
            <div className="p-3 rounded-xl border border-white/[0.06] bg-white/[0.02] text-xs text-slate-400 space-y-2">
              <p>No indexed documents yet.</p>
              <Link
                href="/dashboard"
                className="inline-block text-indigo-400 hover:text-indigo-300 underline"
              >
                Upload a PDF →
              </Link>
            </div>
          ) : (
            <div className="flex flex-col gap-1.5">
              {docs.map((doc) => {
                const active = selectedDocs.includes(doc.id);
                return (
                  <button
                    key={doc.id}
                    onClick={() => toggleDoc(doc.id)}
                    className={`flex items-center gap-2.5 text-left px-3 py-2.5 rounded-xl text-xs border transition-all cursor-pointer ${
                      active
                        ? "border-indigo-500/50 bg-indigo-500/10 text-slate-100"
                        : "border-white/[0.06] bg-white/[0.01] text-slate-400 hover:border-white/15 hover:text-slate-200"
                    }`}
                  >
                    <span
                      className={`w-4 h-4 rounded flex items-center justify-center shrink-0 border ${
                        active
                          ? "bg-indigo-500 border-indigo-500 text-white"
                          : "border-white/15"
                      }`}
                    >
                      {active && <Check className="w-3 h-3" />}
                    </span>
                    <FileText className="w-3.5 h-3.5 shrink-0 text-indigo-400/80" />
                    <span className="truncate">{doc.filename}</span>
                  </button>
                );
              })}
            </div>
          )}
        </aside>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col overflow-hidden bg-grid">
          <div className="flex-1 overflow-y-auto px-6 py-8">
            <div className="max-w-3xl mx-auto flex flex-col gap-6">
              {messages.length === 0 && (
                <div className="py-16 flex flex-col items-center text-center gap-5">
                  <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                    <Sparkles className="w-5 h-5 text-indigo-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-slate-100">
                      Ask your financial documents
                    </h2>
                    <p className="text-sm text-slate-400 mt-1 max-w-md">
                      Select one or more documents on the left, then ask a
                      question or try a prompt below.
                    </p>
                  </div>

                  {selectedDocs.length > 0 && (
                    <div className="flex flex-wrap justify-center gap-2 mt-2">
                      {SAMPLE_PROMPTS.map((prompt) => (
                        <button
                          key={prompt}
                          onClick={() => sendQuestion(prompt)}
                          className="px-3.5 py-2 rounded-xl text-xs border border-white/10 bg-[#0e1017] hover:border-indigo-500/40 hover:bg-indigo-500/5 text-slate-300 transition-all cursor-pointer"
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${
                    msg.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  {msg.role === "user" ? (
                    <div className="max-w-xl px-4 py-3 rounded-2xl rounded-br-sm bg-indigo-500 text-white text-sm leading-relaxed shadow-lg shadow-indigo-500/15">
                      {msg.text}
                    </div>
                  ) : (
                    <div className="max-w-2xl w-full flex gap-3">
                      <div className="w-7 h-7 rounded-lg bg-indigo-500/15 border border-indigo-500/25 flex items-center justify-center shrink-0 mt-0.5">
                        <Bot className="w-4 h-4 text-indigo-400" />
                      </div>
                      <div className="flex-1 flex flex-col gap-2.5">
                        <div className="px-4 py-3.5 rounded-2xl rounded-tl-sm bg-[#0e1017] border border-white/[0.08] text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
                          {msg.text}
                        </div>

                        {msg.confidence && (
                          <div className="flex items-center gap-2">
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium border ${
                                CONFIDENCE_STYLE[msg.confidence] ??
                                "bg-white/5 text-slate-400 border-white/10"
                              }`}
                            >
                              Confidence: {msg.confidence}
                            </span>
                          </div>
                        )}

                        {msg.citations && msg.citations.length > 0 && (
                          <div className="flex flex-col gap-1.5">
                            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500">
                              <Quote className="w-3 h-3" /> Sources
                            </span>
                            <div className="grid gap-1.5">
                              {msg.citations.map((c, ci) => (
                                <div
                                  key={ci}
                                  className="px-3 py-2 rounded-xl text-xs border border-white/[0.06] bg-[#0b0d14] text-slate-400 leading-relaxed"
                                >
                                  <span className="font-mono-code font-medium text-indigo-300 mr-2">
                                    p.{c.page_number}
                                  </span>
                                  {c.content_preview}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="flex gap-3">
                  <div className="w-7 h-7 rounded-lg bg-indigo-500/15 border border-indigo-500/25 flex items-center justify-center shrink-0">
                    <Bot className="w-4 h-4 text-indigo-400" />
                  </div>
                  <div className="inline-flex items-center gap-2 px-4 py-3 rounded-2xl rounded-tl-sm bg-[#0e1017] border border-white/[0.08] text-sm text-slate-400">
                    <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                    Searching documents &amp; verifying citations…
                  </div>
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          </div>

          {/* Input Bar */}
          <div className="shrink-0 border-t border-white/[0.07] bg-[#07080d]/90 backdrop-blur-md px-6 py-4">
            <form
              onSubmit={handleSend}
              className="max-w-3xl mx-auto flex items-center gap-2.5 p-1.5 pl-4 rounded-2xl border border-white/10 bg-[#0e1017] focus-within:border-indigo-500/60 transition-colors"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={
                  selectedDocs.length
                    ? "Ask a question about the selected documents…"
                    : "Select at least one document in the sidebar"
                }
                disabled={!selectedDocs.length || loading}
                className="flex-1 bg-transparent text-sm text-slate-100 placeholder:text-slate-500 outline-none disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!input.trim() || !selectedDocs.length || loading}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium bg-indigo-500 hover:bg-indigo-400 text-white transition-all disabled:opacity-35 cursor-pointer"
              >
                <Send className="w-3.5 h-3.5" />
                Send
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense>
      <ChatApp />
    </Suspense>
  );
}

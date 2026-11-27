const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

// ── Auth ────────────────────────────────────────────────────────────────────

export async function signup(email: string, password: string) {
  return request<{ message: string; email: string }>("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function signin(email: string, password: string) {
  const data = await request<{ access_token: string; token_type: string }>(
    "/api/auth/signin",
    { method: "POST", body: JSON.stringify({ email, password }) }
  );
  localStorage.setItem("token", data.access_token);
  return data;
}

export function signout() {
  localStorage.removeItem("token");
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

// ── Documents ───────────────────────────────────────────────────────────────

export interface Document {
  id: string;
  filename: string;
  status: "QUEUED" | "EXTRACTING" | "COMPLETED" | "FAILED";
  created_at: string;
}

export async function uploadDocument(file: File): Promise<{ doc_id: string }> {
  const form = new FormData();
  form.append("file", file);
  return request<{ doc_id: string }>("/api/documents/upload", {
    method: "POST",
    body: form,
  });
}

export async function listDocuments(): Promise<Document[]> {
  return request<Document[]>("/api/documents/");
}

export async function getDocumentStatus(docId: string): Promise<Document> {
  return request<Document>(`/api/documents/${docId}/status`);
}

// ── Chat ────────────────────────────────────────────────────────────────────

export interface Citation {
  chunk_id: string;
  page_number: number;
  content_preview: string;
  score: number;
}

export interface ChatResponse {
  answer: string;
  confidence: string;
  citations: Citation[];
}

export async function chat(
  question: string,
  docIds: string[]
): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat/", {
    method: "POST",
    body: JSON.stringify({ query:question, doc_ids: docIds }),
  });
}

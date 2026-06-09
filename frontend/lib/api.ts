// Typed client for the ContractIQ FastAPI backend (proxied via /api/* rewrites).
import { getToken } from "./auth";

export type RiskLevel = "HIGH" | "MEDIUM" | "LOW";

/** Headers including the bearer token when a session exists. */
function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = getToken();
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra;
}

export interface Clause {
  clause_id: string;
  clause_type: string;
  original_text: string;
  plain_english_summary: string | null;
  risk_level: RiskLevel | null;
  risk_score: number | null;
  risk_rationale: string | null;
  negotiation_suggestion: string | null;
  is_ambiguous: boolean;
  page_references: number[];
}

export interface Contract {
  contract_id: string;
  filename: string;
  page_count: number;
  chunk_count: number;
  overall_risk_score: number;
  parties: string[];
  contract_type: string;
  governing_law: string;
  status: string;
  warnings: string[];
  clauses: Clause[];
}

export interface QATurn {
  turn_id: string;
  user_query: string;
  agent_answer: string;
  citations: string[];
  retrieved_chunks: { page_num: number; score: number; text: string }[];
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export interface ManagedUser {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "user";
  is_active: boolean;
  created_at: string;
}

export const api = {
  async upload(file: File): Promise<{ contract_id: string; page_count: number; chunk_count: number }> {
    const form = new FormData();
    form.append("file", file);
    return json(await fetch("/api/upload", { method: "POST", headers: authHeaders(), body: form }));
  },

  async analyze(contractId: string): Promise<Contract> {
    return json(await fetch(`/api/analyze/${contractId}`, { method: "POST", headers: authHeaders() }));
  },

  async chat(contractId: string, query: string): Promise<QATurn> {
    return json(
      await fetch(`/api/chat/${contractId}`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ query }),
      })
    );
  },

  /** Download the report as an authenticated blob (Authorization header can't ride on <a href>). */
  async downloadReport(contractId: string, filename: string): Promise<void> {
    const res = await fetch(`/api/export/${contractId}`, { headers: authHeaders() });
    if (!res.ok) throw new Error(`Export failed (${res.status})`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  // --- user management (admin) ---
  async listUsers(): Promise<ManagedUser[]> {
    return json(await fetch("/api/users", { headers: authHeaders() }));
  },
  async updateUser(id: string, patch: Partial<Pick<ManagedUser, "role" | "is_active">>): Promise<ManagedUser> {
    return json(
      await fetch(`/api/users/${id}`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(patch),
      })
    );
  },
  async deleteUser(id: string): Promise<void> {
    const res = await fetch(`/api/users/${id}`, { method: "DELETE", headers: authHeaders() });
    if (!res.ok) throw new Error(`Delete failed (${res.status})`);
  },

  async health(): Promise<{
    status: string;
    llm_provider: string;
    llm_model: string | null;
    llm_ready: boolean;
    embedding_model: string;
    embeddings_ready: boolean;
  }> {
    return json(await fetch("/api/health"));
  },
};

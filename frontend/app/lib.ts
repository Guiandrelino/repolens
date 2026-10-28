export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let message = "Não foi possível concluir a operação.";
    try {
      const data = await response.json();
      message = typeof data.detail === "string" ? data.detail : "Confira os dados informados.";
    } catch { /* resposta não JSON */ }
    throw new Error(message);
  }
  if (response.headers.get("content-type")?.includes("application/json")) return response.json();
  return undefined as T;
}

export type User = { id: string; login: string; avatar_url: string };
export type Health = { mode: "demo" | "live"; demo_login: boolean };
export type Finding = {
  id: string; title: string; severity: "high" | "medium" | "low";
  category: string; path: string; start_line: number; end_line: number;
  evidence: string; description: string; recommendation: string; resolved: boolean;
};
export type Analysis = {
  id: string; repo_url: string; focus: string;
  status: "queued" | "running" | "completed" | "failed";
  mode: "demo" | "live"; commit_sha: string | null;
  summary: string; error: string | null; created_at: string;
  metrics: { input_tokens?: number; output_tokens?: number; tool_calls?: number; duration_seconds?: number; files_loaded?: number; scope_limited?: boolean };
  findings?: Finding[];
};
export const statusLabel = { queued: "Na fila", running: "Em análise", completed: "Concluída", failed: "Falhou" };
export const focusLabel: Record<string, string> = { quality: "Qualidade", architecture: "Arquitetura", tests: "Testes" };
export const severityLabel = { high: "Alto impacto", medium: "Médio impacto", low: "Baixo impacto" };
export function date(value: string) {
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value.endsWith("Z") || /[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`));
}

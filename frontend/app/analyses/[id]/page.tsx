"use client";
import { use, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowUpRight, Check, CheckCircle2, Clock3, Download, FileCode2, GitBranch, Loader2, Search, ShieldCheck, Terminal } from "lucide-react";
import { Shell } from "@/components/shell";
import { API, Analysis, Finding, User, api, date, focusLabel, severityLabel, statusLabel } from "@/app/lib";

export default function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState("");
  const [events, setEvents] = useState<{ sequence: number; message: string }[]>([]);
  const [severity, setSeverity] = useState("all");
  const [resolution, setResolution] = useState("all");
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState<string | null>(null);
  const cursor = useRef(0);
  const load = useCallback(async () => {
    try { setAnalysis(await api<Analysis>(`/analyses/${id}`)); }
    catch (e) { setError(e instanceof Error ? e.message : "Falha ao carregar"); }
  }, [id]);

  useEffect(() => {
    void load();
    void api<User>("/auth/me").then(setUser).catch(() => {});
    const interval = setInterval(load, 4000);
    return () => clearInterval(interval);
  }, [load]);

  useEffect(() => {
    let source: EventSource | null = null;
    let timer: ReturnType<typeof setTimeout>;
    let closed = false;
    cursor.current = 0;
    setEvents([]);
    function connect() {
      source = new EventSource(`${API}/analyses/${id}/events?after=${cursor.current}`, { withCredentials: true });
      source.onmessage = event => {
        const entry = JSON.parse(event.data) as { sequence: number; message: string };
        if (entry.sequence > cursor.current) {
          cursor.current = entry.sequence;
          setEvents(previous => [...previous, entry]);
        }
      };
      source.addEventListener("done", () => { source?.close(); void load(); });
      source.onerror = () => { source?.close(); if (!closed) timer = setTimeout(connect, 5000); };
    }
    connect();
    return () => { closed = true; source?.close(); clearTimeout(timer); };
  }, [id, load]);

  async function toggle(finding: Finding) {
    setSaving(finding.id); setError("");
    try {
      await api(`/analyses/${id}/findings/${finding.id}`, { method: "PATCH", body: JSON.stringify({ resolved: !finding.resolved }) });
      await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível atualizar"); }
    finally { setSaving(null); }
  }

  if (!analysis) return <Shell user={user}><Link className="back-link" href="/"><ArrowLeft size={15}/> Visão geral</Link><div className="empty-state">{error || <><Loader2 className="spin"/> Carregando análise...</>}</div></Shell>;
  const findings = analysis.findings || [];
  const visible = findings.filter(f => (severity === "all" || f.severity === severity) && (resolution === "all" || f.resolved === (resolution === "resolved")) && `${f.title} ${f.path}`.toLowerCase().includes(search.toLowerCase()));
  const isActive = ["running", "queued"].includes(analysis.status);
  const metrics = analysis.metrics;

  return <Shell user={user}>
    <Link className="back-link" href="/"><ArrowLeft size={15}/> Todas as análises</Link>
    <section className="page-heading report-heading"><div><div className="eyebrow"><GitBranch size={14}/> RELATÓRIO DO REPOSITÓRIO</div><h1 className="repo-title">{analysis.repo_url.replace("https://github.com/", "")}</h1><div className="report-meta"><span className={`status ${analysis.status}`}><span/>{statusLabel[analysis.status]}</span><span>{focusLabel[analysis.focus]}</span><span>{date(analysis.created_at)}</span></div></div><a className="button secondary" href={`${API}/analyses/${id}/export`}><Download size={17}/> Exportar Markdown</a></section>
    {analysis.mode === "demo" && <div className="demo-banner"><ShieldCheck size={17}/><span><strong>Relatório de demonstração.</strong> Os trechos abaixo são fictícios e não pertencem à URL informada. Agentes e resultados são simulados.</span></div>}
    {error && <div className="alert error" role="alert">{error}</div>}
    {analysis.error && <div className="alert error" role="alert"><strong>A análise não foi concluída.</strong> {analysis.error}</div>}
    <section className="report-grid"><div className="panel summary-panel"><span className="eyebrow">{isActive ? "INVESTIGAÇÃO EM ANDAMENTO" : "VISÃO GERAL"}</span><h2>{isActive ? "Os agentes estão trabalhando." : "O que encontramos"}</h2><p>{analysis.summary || "Consultando o código e reunindo evidências. Você pode sair desta página e voltar depois."}</p>{analysis.commit_sha && analysis.mode === "live" && <a className="commit-link" href={`${analysis.repo_url}/tree/${analysis.commit_sha}`} target="_blank" rel="noreferrer"><GitBranch size={14}/> Commit {analysis.commit_sha.slice(0, 8)} <ArrowUpRight size={13}/></a>}{metrics.scope_limited && <div className="alert">Análise parcial: nem todos os arquivos elegíveis couberam nos limites de escopo.</div>}<div className="summary-stats"><div><strong>{findings.length}</strong><span>achados revisados</span></div><div><strong>{metrics.files_loaded ?? "—"}</strong><span>arquivos no escopo</span></div><div><strong>{metrics.duration_seconds != null ? `${metrics.duration_seconds}s` : "—"}</strong><span>tempo total</span></div></div></div><div className="panel activity-panel"><div className="section-heading"><h3><Terminal size={16}/> Atividade dos agentes</h3>{isActive && <Loader2 size={16} className="spin accent"/>}</div><div className="activity-log" aria-live="polite">{events.length ? events.map((event, i) => <div key={event.sequence} className="activity-event"><span className={i === events.length - 1 && isActive ? "event-dot pulsing" : "event-dot"}/><p>{event.message}</p></div>) : <p className="muted">Aguardando eventos do processamento...</p>}</div><div className="activity-footer"><span>{metrics.tool_calls ?? 0} chamadas de ferramentas</span><span>{((metrics.input_tokens ?? 0) + (metrics.output_tokens ?? 0)).toLocaleString("pt-BR")} tokens</span></div></div></section>
    <section className="findings-section"><div className="section-heading"><div><h2>Plano de melhorias <span className="count">{findings.length}</span></h2><p>Evidências primeiro. Prioridades depois.</p></div><span className="resolved-count"><CheckCircle2 size={16}/>{findings.filter(f => f.resolved).length} resolvidos</span></div><div className="filter-bar"><div className="search-input"><Search size={16}/><input aria-label="Buscar achado" placeholder="Buscar achado ou arquivo..." value={search} onChange={e => setSearch(e.target.value)}/></div><select className="filter-select" aria-label="Filtrar impacto" value={severity} onChange={e => setSeverity(e.target.value)}><option value="all">Todos os impactos</option>{Object.entries(severityLabel).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><select className="filter-select" aria-label="Filtrar resolução" value={resolution} onChange={e => setResolution(e.target.value)}><option value="all">Todos os estados</option><option value="open">Em aberto</option><option value="resolved">Resolvidos</option></select></div>
      {!visible.length && <div className="panel empty-state">{isActive ? <><Clock3 size={26}/><h3>A revisão ainda está em andamento.</h3><p>Os achados aparecerão após a validação final.</p></> : <><ShieldCheck size={27}/><h3>Nenhum achado para exibir.</h3><p>{findings.length ? "Ajuste os filtros para ver outros resultados." : "Isso não garante ausência de problemas no repositório."}</p></>}</div>}
      {visible.map(f => <article key={f.id} className={`finding-card ${f.resolved ? "is-resolved" : ""}`}><div className="finding-top"><div className="finding-tags"><span className={`severity ${f.severity}`}>{severityLabel[f.severity]}</span><span className="subtle-pill">{focusLabel[f.category] || (f.category === "security" ? "Segurança" : f.category)}</span></div><button className={`resolve-button ${f.resolved ? "checked" : ""}`} disabled={saving === f.id} onClick={() => toggle(f)}>{saving === f.id ? <Loader2 size={15} className="spin"/> : <Check size={15}/>} {f.resolved ? "Resolvido" : "Marcar resolvido"}</button></div><h3>{f.title}</h3><p>{f.description}</p><div className="code-block"><div className="code-header"><span><FileCode2 size={14}/>{f.path}<small>L{f.start_line}–{f.end_line}</small></span>{analysis.mode === "live" && analysis.commit_sha && <a href={`${analysis.repo_url}/blob/${analysis.commit_sha}/${f.path.split("/").map(encodeURIComponent).join("/")}#L${f.start_line}-L${f.end_line}`} target="_blank" rel="noreferrer">Ver no GitHub <ArrowUpRight size={13}/></a>}</div><pre><code>{f.evidence}</code></pre></div><div className="recommendation"><span><ShieldCheck size={16}/> Próximo passo sugerido</span><p>{f.recommendation}</p></div></article>)}
    </section><div className="bottom-note"><ShieldCheck size={15}/> Sugestões para revisão humana. Evidências validadas não garantem que todas as conclusões estejam corretas.</div>
  </Shell>;
}

"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, ArrowUpRight, Check, CheckCheck, ChevronRight, Clock3, Code2, GitBranch, Github, Loader2, Plus, Search, ShieldCheck, Sparkles, X } from "lucide-react";
import { Shell } from "@/components/shell";
import { API, Analysis, Health, User, api, date, focusLabel, statusLabel } from "./lib";

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modal, setModal] = useState(false);
  const [url, setUrl] = useState("");
  const [focus, setFocus] = useState("quality");
  const [busy, setBusy] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    async function load() {
      try {
        setHealth(await api<Health>("/health"));
        const me = await api<User>("/auth/me").catch(() => null);
        setUser(me);
        if (me) setAnalyses(await api<Analysis[]>("/analyses"));
      } catch (e) { setError(e instanceof Error ? e.message : "API indisponível. Verifique se os serviços estão rodando."); }
      finally { setLoading(false); }
    }
    void load();
  }, []);

  async function demoLogin() {
    setBusy(true); setError("");
    try { await api("/auth/demo", { method: "POST" }); setUser(await api<User>("/auth/me")); }
    catch (e) { setError(e instanceof Error ? e.message : "Falha no login"); }
    finally { setBusy(false); }
  }
  async function create(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const result = await api<Analysis>("/analyses", { method: "POST", body: JSON.stringify({ repo_url: url, focus }) });
      router.push(`/analyses/${result.id}`);
    } catch (e) { setError(e instanceof Error ? e.message : "Erro ao criar análise"); setBusy(false); }
  }
  const completed = analyses.filter(a => a.status === "completed").length;
  const active = analyses.filter(a => ["queued", "running"].includes(a.status)).length;
  const visible = analyses.filter(a => a.repo_url.toLowerCase().includes(search.toLowerCase()));

  return <Shell user={user}>
    <section className="page-heading"><div><div className="eyebrow"><span className="live-dot"/> SEU CÓDIGO, SOB UMA NOVA PERSPECTIVA</div><h1>Menos ruído.<br className="mobile-break"/> Mais clareza<span className="accent">.</span></h1><p>Transforme repositórios em decisões técnicas melhores.</p></div><button className="button primary" disabled={!user || loading} onClick={() => { setError(""); setModal(true); }}><Plus size={18}/> Nova análise</button></section>
    {error && !modal && <div className="alert error" role="alert">{error}</div>}
    {health?.mode === "demo" && <div className="demo-banner"><Sparkles size={16}/><span><strong>Ambiente de demonstração.</strong> Relatórios usam arquivos fictícios, sem chamadas à IA ou análise da URL informada.</span><span className="pill">SEM CUSTO DE IA</span></div>}

    <section className="hero-card"><div className="hero-copy"><span className="mini-tag"><Sparkles size={13}/> REVISÃO ASSISTIDA POR IA</span><h2>Um segundo olhar.<br/><span>Com evidências de verdade.</span></h2><p>Agentes investigam o código, revisam os achados e entregam um plano de melhorias. Você mantém o controle.</p><div className="hero-checks"><span><Check size={14}/> Referências ao código</span><span><Check size={14}/> Sem executar arquivos</span></div></div><div className="agent-visual" aria-hidden="true"><div className="visual-grid"/><div className="code-float"><Code2 size={18}/><span>repository / source</span><span className="code-lines">01&nbsp; <i>const</i> insight = await<br/>02&nbsp; &nbsp; agents.review(code);<br/>03&nbsp; <i>return</i> clarity;</span></div><div className="agent-flow"><div><span className="agent-symbol"><Search size={18}/></span><strong>Analista</strong><small>Investiga & conecta</small></div><span className="flow-arrow">→</span><div><span className="agent-symbol green"><ShieldCheck size={18}/></span><strong>Revisor</strong><small>Valida & prioriza</small></div></div><div className="verified"><span className="live-dot"/> Evidência antes de opinião</div></div></section>

    <section className="stats-grid"><div className="stat-card"><span className="stat-icon"><GitBranch size={18}/></span><div><span>Análises criadas</span><strong>{analyses.length.toString().padStart(2, "0")}</strong></div><small>NO SEU WORKSPACE</small></div><div className="stat-card"><span className="stat-icon green"><CheckCheck size={18}/></span><div><span>Relatórios concluídos</span><strong>{completed.toString().padStart(2, "0")}</strong></div><small>PRONTOS PARA REVISAR</small></div><div className="stat-card"><span className="stat-icon amber"><Clock3 size={18}/></span><div><span>Em processamento</span><strong>{active.toString().padStart(2, "0")}</strong></div><small>AGENTES EM AÇÃO</small></div></section>

    {!loading && !user ? <section className="login-panel"><div className="empty-icon"><Github size={27}/></div><h2>Seu próximo insight começa aqui.</h2><p>Entre para criar análises e manter seu histórico organizado.</p><div className="button-row"><a className="button primary" href={`${API}/auth/github`}><Github size={17}/> Entrar com GitHub <ArrowUpRight size={15}/></a>{health?.demo_login && <button className="button secondary" disabled={busy} onClick={demoLogin}>{busy ? <Loader2 size={16} className="spin"/> : <Sparkles size={16}/>} Explorar demonstração</button>}</div><small>Somente repositórios públicos. Nenhuma permissão de escrita.</small></section> : <section className="analyses-panel"><div className="section-heading"><div><h2>Análises recentes <span className="count">{analyses.length}</span></h2><p>Da investigação ao próximo passo.</p></div><div className="search-input"><Search size={16}/><input aria-label="Buscar repositório" placeholder="Buscar repositório..." value={search} onChange={e => setSearch(e.target.value)}/></div></div>
      {loading ? <div className="empty-state"><Loader2 className="spin"/> Carregando workspace...</div> : visible.length ? <div className="table-scroll"><table><thead><tr><th>REPOSITÓRIO</th><th>FOCO</th><th>STATUS</th><th>CRIADA EM</th><th/></tr></thead><tbody>{visible.map(a => <tr key={a.id}><td><Link href={`/analyses/${a.id}`} className="repo-cell"><span className="repo-icon"><GitBranch size={17}/></span><span><strong>{a.repo_url.replace("https://github.com/", "")}</strong><small>{a.mode === "demo" ? "Demonstração · arquivos fictícios" : "Repositório público"}</small></span></Link></td><td><span className="subtle-pill">{focusLabel[a.focus]}</span></td><td><span className={`status ${a.status}`}><span/>{statusLabel[a.status]}</span></td><td className="date-cell">{date(a.created_at)}</td><td><Link aria-label="Abrir análise" className="icon-button" href={`/analyses/${a.id}`}><ChevronRight size={18}/></Link></td></tr>)}</tbody></table></div> : <div className="empty-state"><div className="empty-icon"><GitBranch size={24}/></div><h3>{search ? "Nenhum resultado encontrado" : "Seu workspace está pronto."}</h3><p>{search ? "Tente buscar outro repositório." : "Adicione um repositório e descubra onde melhorar primeiro."}</p>{!search && <button className="text-button" onClick={() => setModal(true)}>Criar primeira análise <ArrowRight size={16}/></button>}</div>}
    </section>}
    <div className="bottom-note"><ShieldCheck size={15}/> Uma ferramenta de apoio à revisão humana. Não substitui testes ou auditoria de segurança.</div>

    {modal && <div className="modal-backdrop" onClick={() => !busy && setModal(false)}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" onClick={e => e.stopPropagation()} onKeyDown={e => { if (e.key === "Escape" && !busy) setModal(false); }}><div className="modal-heading"><span className="empty-icon"><GitBranch size={23}/></span><button className="icon-button" aria-label="Fechar" disabled={busy} onClick={() => setModal(false)}><X size={20}/></button></div><h2 id="modal-title">Um novo olhar para seu código.</h2><p>Informe um repositório público de JavaScript ou TypeScript.</p><form onSubmit={create}><label htmlFor="repo-url">URL do repositório</label><input id="repo-url" className="input" type="url" autoFocus required maxLength={300} placeholder="https://github.com/usuario/projeto" value={url} onChange={e => setUrl(e.target.value)}/><label htmlFor="focus">Foco da análise</label><select id="focus" className="input" value={focus} onChange={e => setFocus(e.target.value)}>{Object.entries(focusLabel).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select><div className="form-note"><ShieldCheck size={16}/>{health?.mode === "demo" ? "Modo demo: a URL será apenas um rótulo. O resultado usa arquivos fictícios." : "Até 60 arquivos, sem executar código. Conteúdos selecionados serão enviados ao provedor de IA."}</div>{error && <div className="alert error" role="alert">{error}</div>}<button className="button primary full" disabled={busy}>{busy ? <Loader2 size={17} className="spin"/> : <Sparkles size={17}/>} {busy ? "Enviando..." : "Iniciar análise"}<ArrowRight size={16}/></button></form></section></div>}
  </Shell>;
}

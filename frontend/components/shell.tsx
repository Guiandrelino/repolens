"use client";
import Link from "next/link";
import { ArrowUpRight, BookOpen, Boxes, Github, LogOut, ScanLine, ShieldCheck } from "lucide-react";
import { API, api, User } from "@/app/lib";

export function Shell({ children, user, onLogout }: { children: React.ReactNode; user?: User | null; onLogout?: () => void }) {
  return <div className="app-shell">
    <aside className="sidebar">
      <Link className="brand" href="/"><span className="brand-icon"><ScanLine size={23}/></span>repo<span>lens</span><span className="brand-dot">.</span></Link>
      <div className="workspace-label">WORKSPACE</div>
      <Link className="nav-link active" href="/"><Boxes size={18}/> Visão geral <span className="nav-dot"/></Link>
      <a className="nav-link" href={`${API}/docs`} target="_blank" rel="noreferrer"><BookOpen size={18}/> API & documentação <ArrowUpRight size={14}/></a>
      <div className="sidebar-bottom"><div className="safety"><ShieldCheck size={19}/><strong>Seu código, só leitura.</strong><p>Investigamos evidências. Nunca executamos o repositório.</p></div>
        {user && <div className="user-box"><span className="avatar">{user.login.slice(0, 2).toUpperCase()}</span><div><strong>{user.login}</strong><small>Workspace pessoal</small></div><button aria-label="Sair" className="icon-button" onClick={async () => { try { await api("/auth/logout", { method: "POST" }); onLogout?.(); window.location.href = "/"; } catch { window.alert("Não foi possível sair. Tente novamente."); } }}><LogOut size={16}/></button></div>}
      </div>
    </aside>
    <div className="main-area"><header className="topbar"><span>Workspace <span className="slash">/</span> <strong>Análises de código</strong></span><a href="https://github.com" target="_blank" rel="noreferrer"><Github size={16}/> GitHub <ArrowUpRight size={13}/></a></header><main>{children}</main><footer>Construído para entender, não apenas apontar. <span>RepoLens · v1.0</span></footer></div>
  </div>;
}

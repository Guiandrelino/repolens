import asyncio
import json
from datetime import timedelta

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import current_user
from .auth import router as auth_router
from .config import get_settings
from .db import SessionLocal, get_db
from .models import Analysis, AnalysisEvent, Finding, User, now
from .schemas import AnalysisCreate, ResolveUpdate
from .tasks import analyze_repository

settings = get_settings()
app = FastAPI(title="RepoLens API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def protect_requests(request: Request, call_next):
    if (
        request.method in {"POST", "PATCH", "PUT", "DELETE"}
        and request.headers.get("origin") != settings.frontend_url
    ):
        return PlainTextResponse("Origem não permitida.", status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(auth_router)


def owned(db, analysis_id, user_id):
    analysis = db.get(Analysis, analysis_id)
    if not analysis or analysis.user_id != user_id:
        raise HTTPException(404, "Análise não encontrada.")
    return analysis


def serialize(row):
    return {
        column.name: getattr(row, column.name) for column in row.__table__.columns if column.name != "user_id"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": settings.analysis_mode,
        "demo_login": settings.allow_demo_login and settings.analysis_mode == "demo",
    }


@app.get("/analyses")
def list_analyses(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Analysis).where(Analysis.user_id == user.id).order_by(Analysis.created_at.desc()).limit(100)
    )
    return [serialize(row) for row in rows]


@app.post("/analyses", status_code=202)
def create_analysis(body: AnalysisCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    # Serializa criações por usuário no PostgreSQL para impor limites concorrentes.
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    active = db.scalar(
        select(func.count())
        .select_from(Analysis)
        .where(Analysis.user_id == user.id, Analysis.status.in_(["queued", "running"]))
    )
    recent = db.scalar(
        select(func.count())
        .select_from(Analysis)
        .where(Analysis.user_id == user.id, Analysis.created_at >= now() - timedelta(hours=1))
    )
    if active or recent >= 10:
        raise HTTPException(429, "Aguarde a análise atual. Limite de 10 análises por hora.")
    analysis = Analysis(
        user_id=user.id, repo_url=body.repo_url, focus=body.focus, mode=settings.analysis_mode
    )
    db.add(analysis)
    db.commit()
    try:
        analyze_repository.delay(analysis.id)
    except Exception:
        analysis.status = "failed"
        analysis.error = "Fila indisponível. Verifique Redis e worker e crie uma nova análise."
        db.commit()
    return serialize(analysis)


@app.get("/analyses/{analysis_id}")
def detail(analysis_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    analysis = owned(db, analysis_id, user.id)
    findings = db.scalars(select(Finding).where(Finding.analysis_id == analysis.id)).all()
    return {**serialize(analysis), "findings": [serialize(f) for f in findings]}


@app.patch("/analyses/{analysis_id}/findings/{finding_id}")
def resolve(
    analysis_id: str,
    finding_id: str,
    body: ResolveUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    owned(db, analysis_id, user.id)
    finding = db.get(Finding, finding_id)
    if not finding or finding.analysis_id != analysis_id:
        raise HTTPException(404, "Achado não encontrado.")
    finding.resolved = body.resolved
    db.commit()
    return serialize(finding)


@app.get("/analyses/{analysis_id}/events")
def events(
    analysis_id: str,
    request: Request,
    after: int = 0,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    owned(db, analysis_id, user.id)

    async def stream():
        cursor = max(0, after)
        for _ in range(240):
            if await request.is_disconnected():
                break
            with SessionLocal() as session:
                rows = session.scalars(
                    select(AnalysisEvent)
                    .where(AnalysisEvent.analysis_id == analysis_id, AnalysisEvent.sequence > cursor)
                    .order_by(AnalysisEvent.sequence)
                ).all()
                for row in rows:
                    cursor = row.sequence
                    yield f"id: {cursor}\ndata: {json.dumps({'sequence': cursor, 'message': row.message}, ensure_ascii=False)}\n\n"
                analysis = session.get(Analysis, analysis_id)
                if analysis.status in {"completed", "failed"}:
                    yield "event: done\ndata: {}\n\n"
                    return
            yield ": heartbeat\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/analyses/{analysis_id}/export")
def export(analysis_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    analysis = owned(db, analysis_id, user.id)
    findings = db.scalars(select(Finding).where(Finding.analysis_id == analysis.id)).all()
    lines = [
        "# RepoLens",
        "",
        f"Repositório: {analysis.repo_url}",
        f"Commit: {analysis.commit_sha or '—'}",
        f"Modo: {analysis.mode}",
        "",
        analysis.summary,
        "",
        "Sugestões para revisão humana; não constitui auditoria de segurança.",
    ]
    for finding in findings:
        lines += [
            "",
            f"## [{finding.severity}] {finding.title}",
            f"Arquivo: {finding.path}:{finding.start_line}-{finding.end_line}",
            f"Resolvido: {'sim' if finding.resolved else 'não'}",
            "",
            finding.description,
            "",
            "````text",
            finding.evidence,
            "````",
            "",
            finding.recommendation,
        ]
    return PlainTextResponse(
        "\n".join(lines),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="repolens-{analysis.id}.md"'},
    )

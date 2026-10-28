import logging
from time import monotonic

from celery import Celery
from sqlalchemy import func, select, update

from .agents import demo_report, run_agents
from .config import get_settings
from .db import SessionLocal
from .models import Analysis, AnalysisEvent, Finding, now
from .repository import DEMO_FILES, Repository, load_repository

settings = get_settings()
celery = Celery("repolens", broker=settings.redis_url)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_time_limit=360,
    broker_connection_retry_on_startup=True,
)
logger = logging.getLogger(__name__)


@celery.task(name="analyze_repository")
def analyze_repository(analysis_id):
    with SessionLocal() as db:
        claimed = db.execute(
            update(Analysis)
            .where(Analysis.id == analysis_id, Analysis.status == "queued")
            .values(status="running")
        )
        db.commit()
        if not claimed.rowcount:
            return
        analysis = db.get(Analysis, analysis_id)
        started = monotonic()

        def emit(message):
            sequence = (
                db.scalar(
                    select(func.max(AnalysisEvent.sequence)).where(AnalysisEvent.analysis_id == analysis_id)
                )
                or 0
            )
            db.add(AnalysisEvent(analysis_id=analysis_id, sequence=sequence + 1, message=message))
            db.commit()

        try:
            emit("Iniciando análise em modo " + analysis.mode)
            repo = (
                Repository(DEMO_FILES, "0" * 40)
                if analysis.mode == "demo"
                else load_repository(analysis.repo_url)
            )
            analysis.commit_sha = repo.sha
            db.commit()
            emit(f"Escopo carregado: {len(repo.files)} arquivos. Nenhum código será executado.")
            if analysis.mode == "demo":
                emit("Demonstração: analista e revisor simulados sobre arquivos fictícios.")
                report, metrics = demo_report(repo), {"input_tokens": 0, "output_tokens": 0, "tool_calls": 0}
            else:
                report, metrics = run_agents(repo, analysis.focus, emit)
            for item in report["findings"]:
                db.add(Finding(analysis_id=analysis_id, **item))
            analysis.summary = report["summary"]
            analysis.metrics = {
                **metrics,
                "duration_seconds": round(monotonic() - started, 2),
                "files_loaded": len(repo.files),
                "eligible_files": repo.total_files,
                "scope_limited": repo.truncated,
            }
            analysis.status = "completed"
            analysis.finished_at = now()
            emit("Relatório concluído. Sugestões exigem revisão humana.")
        except Exception as exc:
            db.rollback()
            logger.exception("Analysis failed: %s", analysis_id)
            analysis = db.get(Analysis, analysis_id)
            analysis.status = "failed"
            analysis.error = (
                str(exc)[:400]
                if isinstance(exc, ValueError)
                else "Falha na integração externa. Confira a configuração e os logs do worker."
            )
            analysis.finished_at = now()
            db.commit()
            emit("Análise interrompida. Consulte a mensagem de erro no relatório.")

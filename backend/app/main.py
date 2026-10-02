from contextlib import asynccontextmanager
import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.rate_limit import limiter
from app.modules.auth.router import router as auth_router
from app.modules.academic_years.router import router as academic_years_router
from app.modules.series.router import router as series_router
from app.modules.students.router import router as students_router
from app.modules.classes.router import router as classes_router
from app.modules.enrollments.router import router as enrollments_router
from app.modules.subjects.router import router as subjects_router
from app.modules.teachers.router import router as teachers_router
from app.modules.allocations.router import router as allocations_router
from app.modules.schedule.router import router as schedule_router
from app.modules.attendance.router import router as attendance_router
from app.modules.assessment.router import router as assessment_router
from app.modules.reports.router import router as reports_router
from app.modules.academic_config.router import router as academic_config_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.agenda.router import router as agenda_router
from app.modules.financial.router import router as financial_router
from app.modules.bracelets.router import router as bracelets_router
from app.modules.professor.router import router as professor_router
from app.modules.boletim.router import router as boletim_router
from app.modules.system_config.router import router as system_config_router
from app.modules.cantina.router import router as cantina_router
from app.modules.cantina.programacao_router import router as programacao_router
from app.modules.communication.router import router as communication_router
from app.modules.document_requests.router import router as document_requests_router
from app.modules.ai.router import router as ai_router

API_PREFIX = "/api/v1"

# Usa o logger do servidor para que o diagnóstico apareça no log do container.
logger = logging.getLogger("uvicorn.error")


async def _verificar_migrations() -> None:
    """Diagnóstico de schema: loga erro claro se o banco não estiver no head.

    Evita o sintoma confuso de endpoints retornando 500 genérico
    (`relation ... does not exist`) quando o banco está atrás das migrations.
    """
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from sqlalchemy import text

        from app.database import engine

        script = ScriptDirectory.from_config(Config("alembic.ini"))
        esperado = set(script.get_heads())

        async with engine.connect() as conn:
            try:
                resultado = await conn.execute(text("SELECT version_num FROM alembic_version"))
                atual = {linha[0] for linha in resultado}
            except Exception:
                logger.error(
                    "Banco sem controle de migrations (tabela alembic_version ausente). "
                    "Rode: alembic upgrade head",
                )
                return

        if atual != esperado:
            logger.error(
                "BANCO DESATUALIZADO: revision atual=%s, esperada=%s. "
                "Rode: alembic upgrade head (endpoints novos podem retornar 500).",
                sorted(atual), sorted(esperado),
            )
        else:
            logger.info("Migrations em dia (revision %s)", sorted(atual))
    except Exception:
        logger.warning("Não foi possível verificar o estado das migrations", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import SessionLocal
    from app.modules.boletim.scheduler import PrazoScheduler
    from app.modules.cantina.scheduler import CantinaScheduler
    from app.modules.communication.scheduler import (
        AvisoEscalonamentoScheduler,
        PushReceiptScheduler,
    )

    await _verificar_migrations()

    prazo_scheduler = PrazoScheduler()
    cantina_scheduler = CantinaScheduler()
    aviso_scheduler = AvisoEscalonamentoScheduler()
    push_receipt_scheduler = PushReceiptScheduler()
    app.state.prazo_scheduler = prazo_scheduler
    app.state.cantina_scheduler = cantina_scheduler
    app.state.aviso_scheduler = aviso_scheduler
    app.state.push_receipt_scheduler = push_receipt_scheduler

    await prazo_scheduler.start(SessionLocal)
    await cantina_scheduler.start(SessionLocal)
    await aviso_scheduler.start(SessionLocal)
    await push_receipt_scheduler.start(SessionLocal)
    yield
    await prazo_scheduler.shutdown()
    await cantina_scheduler.shutdown()
    await aviso_scheduler.shutdown()
    await push_receipt_scheduler.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.ENV == "local" else None,
        redoc_url="/redoc" if settings.ENV == "local" else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Rate Limiting
    app.state.limiter = limiter
    app.add_exception_handler(429, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Exception Handlers
    register_exception_handlers(app)

    # Routers
    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(academic_years_router, prefix=API_PREFIX)
    app.include_router(series_router, prefix=API_PREFIX)
    app.include_router(students_router, prefix=API_PREFIX)
    app.include_router(classes_router, prefix=API_PREFIX)
    app.include_router(enrollments_router, prefix=API_PREFIX)
    app.include_router(subjects_router, prefix=API_PREFIX)
    app.include_router(teachers_router, prefix=API_PREFIX)
    app.include_router(allocations_router, prefix=API_PREFIX)
    app.include_router(schedule_router, prefix=API_PREFIX)
    app.include_router(attendance_router, prefix=API_PREFIX)
    app.include_router(assessment_router, prefix=API_PREFIX)
    app.include_router(reports_router, prefix=API_PREFIX)
    app.include_router(academic_config_router, prefix=API_PREFIX)
    app.include_router(dashboard_router, prefix=API_PREFIX)
    app.include_router(agenda_router, prefix=API_PREFIX)
    app.include_router(financial_router, prefix=API_PREFIX)
    app.include_router(bracelets_router, prefix=API_PREFIX)
    app.include_router(professor_router, prefix=API_PREFIX)
    app.include_router(boletim_router, prefix=API_PREFIX)
    app.include_router(system_config_router, prefix=API_PREFIX)
    app.include_router(cantina_router, prefix=API_PREFIX)
    app.include_router(programacao_router, prefix=API_PREFIX)
    app.include_router(communication_router, prefix=API_PREFIX)
    app.include_router(document_requests_router, prefix=API_PREFIX)
    # IA local "Atena". Módulo desacoplado e opcional: registered sempre, mas
    # nenhuma rota depende do Ollama estar no ar.
    app.include_router(ai_router, prefix=API_PREFIX)

    # Static files
    app.mount("/storage", StaticFiles(directory="storage"), name="storage")

    # Health Check
    health_router = APIRouter()

    @health_router.get("/health")
    async def health():
        return {"status": "ok", "version": settings.APP_VERSION, "environment": settings.ENV}

    app.include_router(health_router, prefix=API_PREFIX)

    return app


app = create_app()

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.modules.auth.router import router as auth_router
from app.modules.academic_years.router import router as academic_years_router
from app.modules.series.router import router as series_router
from app.modules.students.router import router as students_router
from app.modules.classes.router import router as classes_router
from app.modules.enrollments.router import router as enrollments_router
from app.modules.subjects.router import router as subjects_router
from app.modules.teachers.router import router as teachers_router
from app.modules.allocations.router import router as allocations_router
from app.modules.attendance.router import router as attendance_router
from app.modules.assessment.router import router as assessment_router
from app.modules.reports.router import router as reports_router
from app.modules.academic_config.router import router as academic_config_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.agenda.router import router as agenda_router

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


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
    limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])
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
    app.include_router(attendance_router, prefix=API_PREFIX)
    app.include_router(assessment_router, prefix=API_PREFIX)
    app.include_router(reports_router, prefix=API_PREFIX)
    app.include_router(academic_config_router, prefix=API_PREFIX)
    app.include_router(dashboard_router, prefix=API_PREFIX)
    app.include_router(agenda_router, prefix=API_PREFIX)

    # Health Check
    health_router = APIRouter()

    @health_router.get("/health")
    async def health():
        return {"status": "ok", "version": settings.APP_VERSION, "environment": settings.ENV}

    app.include_router(health_router, prefix=API_PREFIX)

    return app


app = create_app()

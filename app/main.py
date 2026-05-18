from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.analytics import NHANESAnalyticsService


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

TAGS_METADATA = [
    {"name": "Site", "description": "产品网站与前端展示页面。"},
    {"name": "Platform", "description": "平台健康状态、能力声明与数据目录。"},
    {"name": "Analytics", "description": "人群画像、摘要指标与优先级群体分析。"},
    {"name": "Simulation", "description": "阈值模拟、风险模式与风险因素线索。"},
    {"name": "Reports", "description": "面向不同角色的报告与摘要输出。"},
]

NAV_ITEMS = [
    {"key": "home", "label": "首页", "href": "/"},
    {"key": "scenarios", "label": "应用场景", "href": "/scenarios"},
    {"key": "examples", "label": "落地实例", "href": "/examples"},
    {"key": "studio", "label": "API 展示台", "href": "/studio"},
    {"key": "reports", "label": "报告中心", "href": "/reports"},
    {"key": "vision", "label": "全球视野", "href": "/vision"},
]

app = FastAPI(
    title="HealthInsight API",
    summary="面向公共卫生与心理健康机构的健康洞察 API。",
    description=(
        "基于 NHANES 人口学、睡眠与体力活动模块构建的机构级健康洞察 API，"
        "支持数据体检、人群画像、优先级群体识别与角色化摘要输出。"
    ),
    version="1.0.0",
    contact={"name": "HealthInsight Project"},
    openapi_tags=TAGS_METADATA,
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@lru_cache
def get_service() -> NHANESAnalyticsService:
    return NHANESAnalyticsService(PROJECT_DIR)


def error_response(
    code: str, message: str, details: dict[str, Any] | None = None, status_code: int = 400
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
    )


def page_context(active_page: str, **extra: Any) -> dict[str, Any]:
    return {"nav_items": NAV_ITEMS, "active_page": active_page, **extra}


@app.exception_handler(ValueError)
async def handle_value_error(_: Request, exc: ValueError) -> JSONResponse:
    return error_response("invalid_parameter", str(exc))


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(
        "validation_error",
        "请求参数不合法。",
        {"errors": exc.errors()},
    )


@app.exception_handler(HTTPException)
async def handle_http_error(_: Request, exc: HTTPException) -> JSONResponse:
    return error_response("http_error", str(exc.detail), status_code=exc.status_code)


@app.get("/", response_class=HTMLResponse, tags=["Site"])
async def homepage(request: Request) -> HTMLResponse:
    service = get_service()
    summary = service.summary()
    cohorts = service.priority_cohorts(limit=6, min_participants=100)
    manager_report = service.audience_report("manager")
    risk_factors = service.risk_factors(limit=4, min_participants=120)
    profile = service.population_profile("age_band", min_participants=100)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=page_context(
            "home",
            summary=summary,
            cohorts=cohorts,
            manager_report=manager_report,
            risk_factors=risk_factors,
            profile=profile,
            profile_json=json.dumps(profile, ensure_ascii=False, indent=2),
            summary_json=json.dumps(summary, ensure_ascii=False, indent=2),
        ),
    )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> RedirectResponse:
    return RedirectResponse(url="/static/favicon.svg", status_code=307)


@app.get("/scenarios", response_class=HTMLResponse, tags=["Site"])
async def scenarios_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="scenarios.html",
        context=page_context("scenarios"),
    )


@app.get("/studio", response_class=HTMLResponse, tags=["Site"])
async def studio_page(request: Request) -> HTMLResponse:
    service = get_service()
    summary = service.summary()
    cohorts = service.priority_cohorts(limit=6, min_participants=100)
    risk_factors = service.risk_factors(limit=6, min_participants=120)
    threshold = service.threshold_simulation(threshold=10, weekly_capacity=20)
    return templates.TemplateResponse(
        request=request,
        name="studio.html",
        context=page_context(
            "studio",
            summary=summary,
            cohorts=cohorts,
            risk_factors=risk_factors,
            threshold=threshold,
            summary_json=json.dumps(summary, ensure_ascii=False, indent=2),
            threshold_json=json.dumps(threshold, ensure_ascii=False, indent=2),
        ),
    )


@app.get("/examples", response_class=HTMLResponse, tags=["Site"])
async def examples_page(request: Request) -> HTMLResponse:
    service = get_service()
    summary = service.summary()
    cohorts = service.priority_cohorts(limit=4, min_participants=100)
    manager_report = service.audience_report("manager")
    return templates.TemplateResponse(
        request=request,
        name="examples.html",
        context=page_context(
            "examples",
            summary=summary,
            cohorts=cohorts,
            manager_report=manager_report,
        ),
    )


@app.get("/reports", response_class=HTMLResponse, tags=["Site"])
async def reports_page(request: Request) -> HTMLResponse:
    initial_report = get_service().audience_report("researcher")
    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context=page_context(
            "reports",
            initial_report=initial_report,
            initial_report_json=json.dumps(initial_report, ensure_ascii=False, indent=2),
        ),
    )


@app.get("/vision", response_class=HTMLResponse, tags=["Site"])
async def vision_page(request: Request) -> HTMLResponse:
    service = get_service()
    capabilities = service.capabilities()
    summary = service.summary()
    return templates.TemplateResponse(
        request=request,
        name="vision.html",
        context=page_context(
            "vision",
            capabilities=capabilities,
            summary=summary,
        ),
    )


@app.get("/api/v1/health", tags=["Platform"])
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": "HealthInsight API", "version": "1.0.0"}


@app.get("/api/v1/capabilities", tags=["Platform"])
async def capabilities() -> dict[str, Any]:
    return get_service().capabilities()


@app.get("/api/v1/datasets", tags=["Platform"])
async def datasets() -> dict[str, Any]:
    return get_service().datasets_catalog()


@app.get("/api/v1/summary", tags=["Analytics"])
async def summary() -> dict[str, Any]:
    return get_service().summary()


@app.get("/api/v1/population-profile", tags=["Analytics"])
async def population_profile(
    group_by: str = Query(
        "age_band",
        description=(
            "可选值：age_band、gender、race_ethnicity、income_band、education_band、"
            "sleep_band、bmi_band、chronic_band、priority_tier、phq_severity_band。"
        ),
    ),
    min_age: int = Query(18, ge=18, le=80),
    max_age: int = Query(80, ge=18, le=80),
    min_participants: int = Query(50, ge=10, le=500),
) -> dict[str, Any]:
    if min_age > max_age:
        raise ValueError("min_age 不能大于 max_age")
    return get_service().population_profile(
        group_by=group_by,
        min_age=min_age,
        max_age=max_age,
        min_participants=min_participants,
    )


@app.get("/api/v1/priority-cohorts", tags=["Analytics"])
async def priority_cohorts(
    limit: int = Query(8, ge=1, le=20),
    min_participants: int = Query(80, ge=20, le=500),
) -> dict[str, Any]:
    return get_service().priority_cohorts(limit=limit, min_participants=min_participants)


@app.get("/api/v1/risk-patterns", tags=["Simulation"])
async def risk_patterns(
    limit: int = Query(6, ge=1, le=20),
    min_participants: int = Query(60, ge=20, le=500),
) -> dict[str, Any]:
    return get_service().risk_patterns(limit=limit, min_participants=min_participants)


@app.get("/api/v1/risk-factors", tags=["Simulation"])
async def risk_factors(
    limit: int = Query(8, ge=1, le=20),
    min_participants: int = Query(120, ge=20, le=1000),
) -> dict[str, Any]:
    return get_service().risk_factors(limit=limit, min_participants=min_participants)


@app.get("/api/v1/threshold-simulate", tags=["Simulation"])
async def threshold_simulate(
    threshold: int = Query(10, ge=0, le=27),
    weekly_capacity: int = Query(20, ge=1, le=10000),
) -> dict[str, Any]:
    return get_service().threshold_simulation(
        threshold=threshold,
        weekly_capacity=weekly_capacity,
    )


@app.get("/api/v1/reports/{audience}", tags=["Reports"])
async def report(audience: str) -> dict[str, Any]:
    return get_service().audience_report(audience)

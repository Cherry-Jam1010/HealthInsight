from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DOCS_DIR = PROJECT_DIR / "docs"

TAGS_METADATA = [
    {"name": "Site", "description": "产品网站与前端展示页面。"},
    {"name": "Platform", "description": "平台状态、能力说明与数据目录。"},
    {"name": "Analytics", "description": "风险画像、摘要指标与重点人群分析。"},
    {"name": "Simulation", "description": "阈值模拟、双周期对照与风险线索。"},
    {"name": "Reports", "description": "面向不同角色的简报输出。"},
]

NAV_ITEMS = [
    {"key": "home", "label": "首页", "href": "/"},
    {"key": "scenarios", "label": "应用场景", "href": "/scenarios"},
    {"key": "examples", "label": "落地实例", "href": "/examples"},
    {"key": "guide", "label": "使用指南", "href": "/guide"},
    {"key": "studio", "label": "在线演示", "href": "/studio"},
    {"key": "reports", "label": "报告中心", "href": "/reports"},
    {"key": "vision", "label": "全球视野", "href": "/vision"},
]

app = FastAPI(
    title="HealthInsight API",
    summary="面向公共卫生与心理健康机构的双数据源风险洞察 API。",
    description=(
        "平台同时使用当前 NHANES 心理健康数据与历史行为基线数据，"
        "支持 PHQ-9 风险画像、重点人群识别、阈值模拟与机构级简报输出。"
    ),
    version="2.1.0",
    contact={"name": "HealthInsight Project"},
    openapi_tags=TAGS_METADATA,
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@lru_cache
def get_service() -> Any:
    from app.analytics import NHANESAnalyticsService

    return NHANESAnalyticsService(PROJECT_DIR)


def error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    status_code: int = 400,
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
    return HTMLResponse(
        """
        <!DOCTYPE html>
        <html lang="zh-CN">
          <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>HealthInsight</title>
            <style>
              body {
                margin: 0;
                padding: 48px 24px;
                font-family: Arial, sans-serif;
                background: #f4f8f8;
                color: #173843;
              }
              .shell {
                max-width: 900px;
                margin: 0 auto;
                background: #ffffff;
                border-radius: 20px;
                padding: 36px;
                box-shadow: 0 16px 40px rgba(20, 56, 67, 0.08);
              }
              h1 {
                margin-top: 0;
              }
              .links {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                margin-top: 24px;
              }
              a {
                display: inline-block;
                padding: 12px 16px;
                border-radius: 999px;
                background: #0c7a77;
                color: white;
                text-decoration: none;
              }
              a.secondary {
                background: #d7ece8;
                color: #173843;
              }
            </style>
          </head>
          <body>
            <div class="shell">
              <h1>HealthInsight</h1>
              <p>机构级心理健康风险洞察平台。</p>
              <p>如果首页可以打开，说明应用已经正常启动。后续可继续访问使用指南、在线演示和接口文档。</p>
              <div class="links">
                <a href="/guide">使用指南</a>
                <a href="/studio">在线演示</a>
                <a href="/reports">报告中心</a>
                <a class="secondary" href="/docs">接口文档</a>
              </div>
            </div>
          </body>
        </html>
        """
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
    comparison = service.cycle_comparison("age_band", min_participants=100)
    return templates.TemplateResponse(
        request=request,
        name="studio.html",
        context=page_context(
            "studio",
            summary=summary,
            cohorts=cohorts,
            risk_factors=risk_factors,
            threshold=threshold,
            comparison=comparison,
            summary_json=json.dumps(summary, ensure_ascii=False, indent=2),
            threshold_json=json.dumps(threshold, ensure_ascii=False, indent=2),
            comparison_json=json.dumps(comparison, ensure_ascii=False, indent=2),
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


@app.get("/guide", response_class=HTMLResponse, tags=["Site"])
async def guide_page(request: Request) -> HTMLResponse:
    service = get_service()
    summary = service.summary()
    comparison = service.cycle_comparison("age_band", min_participants=100)
    return templates.TemplateResponse(
        request=request,
        name="guide.html",
        context=page_context(
            "guide",
            summary=summary,
            comparison=comparison,
            summary_json=json.dumps(summary, ensure_ascii=False, indent=2),
            comparison_json=json.dumps(comparison, ensure_ascii=False, indent=2),
        ),
    )


@app.get("/downloads/quickstart", tags=["Site"])
async def download_quickstart() -> FileResponse:
    return FileResponse(
        DOCS_DIR / "HealthInsight_API_Quickstart_CN.md",
        filename="HealthInsight_API_Quickstart_CN.md",
        media_type="text/markdown",
    )


@app.get("/downloads/api-strategy", tags=["Site"])
async def download_api_strategy() -> FileResponse:
    return FileResponse(
        PROJECT_DIR / "API_STRATEGY.md",
        filename="HealthInsight_API_Strategy_CN.md",
        media_type="text/markdown",
    )


@app.get("/downloads/readme", tags=["Site"])
async def download_readme() -> FileResponse:
    return FileResponse(
        PROJECT_DIR / "README.md",
        filename="HealthInsight_README_CN.md",
        media_type="text/markdown",
    )


@app.get("/downloads/openapi", tags=["Site"])
async def download_openapi() -> RedirectResponse:
    return RedirectResponse(url="/api/v1/openapi.json", status_code=307)


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
    return {"status": "ok", "service": "HealthInsight API", "version": "2.1.0"}


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
            "sleep_band、bmi_band、chronic_band、priority_tier、phq_severity_band"
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


@app.get("/api/v1/cycle-comparison", tags=["Simulation"])
async def cycle_comparison(
    group_by: str = Query(
        "age_band",
        description=(
            "可选值：age_band、gender、race_ethnicity、income_band、education_band、sleep_band"
        ),
    ),
    min_age: int = Query(18, ge=18, le=80),
    max_age: int = Query(80, ge=18, le=80),
    min_participants: int = Query(80, ge=20, le=500),
) -> dict[str, Any]:
    if min_age > max_age:
        raise ValueError("min_age 不能大于 max_age")
    return get_service().cycle_comparison(
        group_by=group_by,
        min_age=min_age,
        max_age=max_age,
        min_participants=min_participants,
    )


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

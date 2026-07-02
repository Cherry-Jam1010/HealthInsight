from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.analytics import NHANESAnalyticsService


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

NAV_GROUPS = [
    {
        "key": "home",
        "label": "首页",
        "href": "/",
    },
    {
        "key": "workbench",
        "label": "工作台",
        "href": "/workbench",
    },
    {
        "key": "reports",
        "label": "报告中心",
        "href": "/reports",
    },
]


class SyntheticDatasetRequest(BaseModel):
    name: str = Field(default="演示样本", min_length=1, max_length=80)
    sample_size: int = Field(default=240, ge=30, le=5000)
    profile: Literal["balanced", "sleep_stress", "older_chronic", "community_outreach"] = (
        "balanced"
    )
    scale: Literal["PHQ-9", "CES-D10"] = "PHQ-9"
    seed: int | None = Field(default=None, ge=0, le=999999)


class ManualRow(BaseModel):
    age: int = Field(ge=18, le=90)
    gender: str = Field(min_length=1, max_length=20)
    sleep_hours: float = Field(ge=0, le=16)
    income_band: str = Field(min_length=1, max_length=40)
    education_band: str = Field(min_length=1, max_length=60)
    bmi: float | None = Field(default=None, ge=10, le=60)
    chronic_condition_count: int = Field(default=0, ge=0, le=10)
    mental_health_score: float = Field(ge=0, le=30)
    weight: float = Field(default=1.0, gt=0, le=100)
    race_ethnicity: str | None = Field(default=None, max_length=60)
    residence_band: str | None = Field(default=None, max_length=40)


class ManualDatasetRequest(BaseModel):
    name: str = Field(default="手工样本", min_length=1, max_length=80)
    scale: Literal["PHQ-9", "CES-D10"] = "PHQ-9"
    rows: list[ManualRow] = Field(min_length=3, max_length=500)

class CSVUploadRequest(BaseModel):
    name: str = Field(default="机构导入样本", min_length=1, max_length=80)
    scale: Literal["PHQ-9", "CES-D10"] = "PHQ-9"
    csv_content: str = Field(min_length=1)


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
def get_service() -> NHANESAnalyticsService:
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
    return {
        "nav_groups": NAV_GROUPS,
        "active_page": active_page,
        **extra,
    }


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
    manager_report = service.audience_report("manager")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=page_context(
            "home",
            summary=summary,
            manager_report=manager_report,
        ),
    )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> RedirectResponse:
    return RedirectResponse(url="/static/favicon.svg", status_code=307)


@app.get("/workbench", response_class=HTMLResponse, tags=["Site"])
async def workbench_page(request: Request) -> HTMLResponse:
    custom_datasets = get_service().list_custom_datasets()
    return templates.TemplateResponse(
        request=request,
        name="workbench_real.html",
        context=page_context(
            "workbench",
            custom_datasets=custom_datasets,
            custom_datasets_json=json.dumps(custom_datasets, ensure_ascii=False, indent=2),
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
    service = get_service()
    initial_report = service.institution_report(dataset="current", audience="manager")
    return templates.TemplateResponse(
        request=request,
        name="reports_real.html",
        context=page_context(
            "reports",
            initial_report=initial_report,
            initial_report_json=json.dumps(initial_report, ensure_ascii=False, indent=2),
            custom_datasets=service.list_custom_datasets(),
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


@app.get("/api/v1/custom-datasets", tags=["Platform"])
async def custom_datasets() -> dict[str, Any]:
    return get_service().list_custom_datasets()


@app.post("/api/v1/custom-datasets/generate", tags=["Platform"])
async def generate_custom_dataset(payload: SyntheticDatasetRequest) -> dict[str, Any]:
    dataset = get_service().generate_demo_dataset(
        label=payload.name,
        sample_size=payload.sample_size,
        profile=payload.profile,
        scale=payload.scale,
        seed=payload.seed,
    )
    return {
        "message": "synthetic dataset generated",
        "dataset": dataset,
        "catalog": get_service().list_custom_datasets(),
    }


@app.post("/api/v1/custom-datasets/manual", tags=["Platform"])
async def create_manual_dataset(payload: ManualDatasetRequest) -> dict[str, Any]:
    dataset = get_service().register_custom_dataset(
        label=payload.name,
        rows=[row.model_dump() for row in payload.rows],
        scale=payload.scale,
        source_kind="manual",
    )
    return {
        "message": "manual dataset registered",
        "dataset": dataset,
        "catalog": get_service().list_custom_datasets(),
    }


@app.post("/api/v1/custom-datasets/upload-csv", tags=["Platform"])
async def upload_csv_dataset(payload: CSVUploadRequest) -> dict[str, Any]:
    result = get_service().import_csv_dataset(
        label=payload.name,
        csv_content=payload.csv_content,
        scale=payload.scale,
    )
    return {
        "message": "csv dataset imported",
        **result,
        "catalog": get_service().list_custom_datasets(),
    }


@app.get("/api/v1/custom-datasets/template", response_class=PlainTextResponse, tags=["Platform"])
async def download_custom_dataset_template() -> PlainTextResponse:
    content = get_service().custom_dataset_csv_template()
    return PlainTextResponse(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="healthinsight_template.csv"'},
    )


@app.get("/api/v1/summary", tags=["Analytics"])
async def summary(
    dataset: str = Query("current", description="current | charls | legacy | custom:{id}"),
) -> dict[str, Any]:
    return get_service().summary(dataset=dataset)


@app.get("/api/v1/population-profile", tags=["Analytics"])
async def population_profile(
    dataset: str = Query("current", description="current | charls | custom:{id}"),
    group_by: str = Query(
        "age_band",
        description=(
            "current 支持 age_band、gender、race_ethnicity、income_band、education_band、"
            "sleep_band、bmi_band、chronic_band、priority_tier；"
            "charls 额外支持 residence_band、hukou_band，并使用 mental_health_severity_band"
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
        dataset=dataset,
        min_age=min_age,
        max_age=max_age,
        min_participants=min_participants,
    )


@app.get("/api/v1/priority-cohorts", tags=["Analytics"])
async def priority_cohorts(
    dataset: str = Query("current", description="current | charls | custom:{id}"),
    limit: int = Query(8, ge=1, le=20),
    min_participants: int = Query(80, ge=3, le=500),
) -> dict[str, Any]:
    return get_service().priority_cohorts(
        limit=limit,
        min_participants=min_participants,
        dataset=dataset,
    )


@app.get("/api/v1/risk-patterns", tags=["Simulation"])
async def risk_patterns(
    dataset: str = Query("current", description="current | charls | custom:{id}"),
    limit: int = Query(6, ge=1, le=20),
    min_participants: int = Query(60, ge=3, le=500),
) -> dict[str, Any]:
    return get_service().risk_patterns(
        limit=limit,
        min_participants=min_participants,
        dataset=dataset,
    )


@app.get("/api/v1/risk-factors", tags=["Simulation"])
async def risk_factors(
    dataset: str = Query("current", description="current | charls | custom:{id}"),
    limit: int = Query(8, ge=1, le=20),
    min_participants: int = Query(120, ge=3, le=1000),
) -> dict[str, Any]:
    return get_service().risk_factors(
        limit=limit,
        min_participants=min_participants,
        dataset=dataset,
    )


@app.get("/api/v1/cycle-comparison", tags=["Simulation"])
async def cycle_comparison(
    dataset: str = Query("current", description="current | charls | custom:{id}"),
    group_by: str = Query(
        "age_band",
        description=(
            "current 支持 age_band、gender、race_ethnicity、income_band、education_band、sleep_band；"
            "charls 支持 age_band、gender、income_band、education_band、sleep_band"
        ),
    ),
    min_age: int = Query(18, ge=18, le=80),
    max_age: int = Query(80, ge=18, le=80),
    min_participants: int = Query(80, ge=3, le=500),
) -> dict[str, Any]:
    if min_age > max_age:
        raise ValueError("min_age 不能大于 max_age")
    return get_service().cycle_comparison(
        group_by=group_by,
        dataset=dataset,
        min_age=min_age,
        max_age=max_age,
        min_participants=min_participants,
    )


@app.get("/api/v1/threshold-simulate", tags=["Simulation"])
async def threshold_simulate(
    dataset: str = Query("current", description="current | charls | custom:{id}"),
    threshold: int = Query(10, ge=0, le=30),
    weekly_capacity: int = Query(20, ge=1, le=10000),
) -> dict[str, Any]:
    return get_service().threshold_simulation(
        threshold=threshold,
        weekly_capacity=weekly_capacity,
        dataset=dataset,
    )


@app.get("/api/v1/reports/{audience}", tags=["Reports"])
async def report(
    audience: str,
    dataset: str = Query("current", description="current | charls | custom:{id}"),
) -> dict[str, Any]:
    return get_service().audience_report(audience, dataset=dataset)


@app.get("/api/v1/institution-report", tags=["Reports"])
async def institution_report(
    dataset: str = Query("current", description="current | charls | custom:{id}"),
    audience: str = Query("manager", description="researcher | manager | clinical | engineering"),
    organization_name: str = Query("示例机构", min_length=1, max_length=120),
    report_title: str | None = Query(None, min_length=1, max_length=160),
    threshold: int | None = Query(None, ge=0, le=30),
    weekly_capacity: int = Query(20, ge=1, le=10000),
) -> dict[str, Any]:
    return get_service().institution_report(
        dataset=dataset,
        audience=audience,
        organization_name=organization_name,
        report_title=report_title,
        threshold=threshold,
        weekly_capacity=weekly_capacity,
    )

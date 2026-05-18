from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path
import shutil
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import numpy as np
import pandas as pd


NUMERIC_SENTINELS = [7, 9, 77, 99, 777, 999, 7777, 9999, 77777, 99999]
TEXT_SENTINELS = {"", "77777", "99999"}
GROUP_FIELDS = {
    "age_band",
    "gender",
    "race_ethnicity",
    "income_band",
    "education_band",
    "sleep_band",
    "bmi_band",
    "chronic_band",
    "priority_tier",
    "phq_severity_band",
}
PHQ_ITEMS = [
    "DPQ010",
    "DPQ020",
    "DPQ030",
    "DPQ040",
    "DPQ050",
    "DPQ060",
    "DPQ070",
    "DPQ080",
    "DPQ090",
]
CHRONIC_CONDITION_LABELS = {
    "MCQ160A": "关节炎",
    "MCQ160B": "充血性心力衰竭",
    "MCQ160C": "冠心病",
    "MCQ160D": "心绞痛",
    "MCQ160E": "心肌梗死",
    "MCQ160F": "卒中",
    "MCQ160M": "甲状腺问题",
    "MCQ160P": "慢阻肺 / 肺气肿 / 慢性支气管炎",
    "MCQ160L": "肝脏疾病",
}
GENDER_LABELS = {
    1.0: "男性",
    2.0: "女性",
}
RACE_ETHNICITY_LABELS = {
    1.0: "墨西哥裔美国人",
    2.0: "其他西班牙裔",
    3.0: "非西班牙裔白人",
    4.0: "非西班牙裔黑人",
    6.0: "非西班牙裔亚裔",
    7.0: "其他 / 多族裔",
}
EDUCATION_LABELS = {
    1.0: "低于9年级",
    2.0: "9-11年级",
    3.0: "高中 / GED",
    4.0: "部分大学 / 副学士",
    5.0: "大学及以上",
}
PRIORITY_TIER_LABELS = {
    0: "常规观察",
    1: "常规观察",
    2: "重点关注",
    3: "重点关注",
    4: "高优先转介",
    5: "高优先转介",
}
DEFAULT_MH_DATA_BASE_URL = os.getenv(
    "HEALTHINSIGHT_MH_DATA_BASE_URL",
    "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles",
)


@dataclass(frozen=True)
class DatasetInfo:
    filename: str
    label: str
    role: str


class NHANESAnalyticsService:
    """Mental-health analytics built on NHANES August 2021-August 2023."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.data_dir = project_dir / "NHANES"
        self.weight_column = "WTMEC2YR"
        self.datasets = [
            DatasetInfo("DEMO_L.xpt", "人口学", "人口学与样本权重"),
            DatasetInfo("DPQ_L.xpt", "PHQ-9 抑郁筛查", "构建 PHQ-9 总分与高风险标签"),
            DatasetInfo("SLQ_L.xpt", "睡眠", "睡眠时长与睡眠分层"),
            DatasetInfo("BMX_L.xpt", "身体测量", "BMI 与腰围等身体指标"),
            DatasetInfo("MCQ_L.xpt", "慢性病与医疗状况", "慢病负担与共病情况"),
        ]
        self._ensure_required_files()
        self.source_frames = {
            info.filename: self._load_xpt(info.filename) for info in self.datasets
        }
        self.analysis_frame = self._prepare_analysis_frame()
        self.phq_ready_frame = self.analysis_frame[
            self.analysis_frame["PHQ9_total"].notna()
        ].copy()
        self.total_weight = float(self.analysis_frame[self.weight_column].dropna().sum())
        self.phq_ready_weight = float(self.phq_ready_frame[self.weight_column].dropna().sum())

    def _ensure_required_files(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        missing = [
            dataset.filename
            for dataset in self.datasets
            if not (self.data_dir / dataset.filename).exists()
        ]
        if not missing:
            return

        base_url = DEFAULT_MH_DATA_BASE_URL.rstrip("/")
        for filename in missing:
            self._download_data_file(base_url, filename)

    def _download_data_file(self, base_url: str, filename: str) -> None:
        target_path = self.data_dir / filename
        temp_path = self.data_dir / f"{filename}.part"
        file_url = f"{base_url}/{filename}"

        try:
            with urlopen(file_url, timeout=120) as response, temp_path.open("wb") as output:
                shutil.copyfileobj(response, output)
            temp_path.replace(target_path)
        except (OSError, URLError) as exc:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(
                f"缺少数据文件 {filename}，并且自动下载失败。"
                f"请检查 {file_url} 是否可访问，或手动放入 NHANES 目录。"
            ) from exc

    def _load_xpt(self, filename: str) -> pd.DataFrame:
        frame = pd.read_sas(self.data_dir / filename, format="xport", encoding="utf-8")
        return self._clean_frame(frame)

    def _clean_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        cleaned = frame.copy()
        for column in cleaned.columns:
            series = cleaned[column]
            if pd.api.types.is_numeric_dtype(series):
                numeric_series = series.astype(float)
                # SAS XPT zeros may appear as tiny floating values after decoding.
                numeric_series = numeric_series.mask(numeric_series.abs() < 1e-70, 0.0)
                cleaned[column] = numeric_series.replace(NUMERIC_SENTINELS, np.nan)
            else:
                cleaned[column] = series.replace(list(TEXT_SENTINELS), np.nan)
        return cleaned

    def _prepare_analysis_frame(self) -> pd.DataFrame:
        demo = self.source_frames["DEMO_L.xpt"].copy()
        dpq = self.source_frames["DPQ_L.xpt"].copy()
        slq = self.source_frames["SLQ_L.xpt"].copy()
        bmx = self.source_frames["BMX_L.xpt"].copy()
        mcq = self.source_frames["MCQ_L.xpt"].copy()

        adults = demo[demo["RIDAGEYR"].fillna(-1) >= 18].copy()
        merged = (
            adults.merge(dpq, on="SEQN", how="left")
            .merge(slq, on="SEQN", how="left")
            .merge(bmx, on="SEQN", how="left")
            .merge(mcq, on="SEQN", how="left")
        )

        merged["gender"] = merged["RIAGENDR"].map(GENDER_LABELS).fillna("未知")
        merged["race_ethnicity"] = (
            merged["RIDRETH3"].map(RACE_ETHNICITY_LABELS).fillna("未知")
        )
        merged["education_band"] = (
            merged["DMDEDUC2"].map(EDUCATION_LABELS).fillna("缺失")
        )

        merged["age_band"] = pd.cut(
            merged["RIDAGEYR"],
            bins=[17, 24, 34, 49, 64, np.inf],
            labels=["18-24", "25-34", "35-49", "50-64", "65+"],
        )
        merged["age_band"] = merged["age_band"].astype("object").fillna("未知")

        merged["income_band"] = pd.cut(
            merged["INDFMPIR"],
            bins=[-np.inf, 1.3, 3.5, np.inf],
            labels=["低收入", "中等收入", "较高收入"],
        )
        merged["income_band"] = merged["income_band"].astype("object").fillna("缺失")

        merged["weekday_sleep_hours"] = merged["SLD012"]
        merged["weekend_sleep_hours"] = merged["SLD013"]
        merged["sleep_gap_hours"] = merged["weekend_sleep_hours"] - merged["weekday_sleep_hours"]

        merged["sleep_band"] = pd.cut(
            merged["weekday_sleep_hours"],
            bins=[-np.inf, 6, 8, np.inf],
            labels=["睡眠不足(<6h)", "正常睡眠(6-8h)", "睡眠偏长(>8h)"],
        )
        merged["sleep_band"] = merged["sleep_band"].astype("object").fillna("缺失")

        merged["BMXBMI"] = merged["BMXBMI"].astype(float)
        merged["bmi_band"] = pd.cut(
            merged["BMXBMI"],
            bins=[-np.inf, 18.5, 25, 30, np.inf],
            labels=["偏瘦", "正常", "超重", "肥胖"],
        )
        merged["bmi_band"] = merged["bmi_band"].astype("object").fillna("缺失")

        chronic_flags: dict[str, pd.Series] = {}
        for column in CHRONIC_CONDITION_LABELS:
            chronic_flags[f"{column}_flag"] = np.where(
                merged[column].notna(),
                merged[column] == 1,
                np.nan,
            )
        chronic_frame = pd.DataFrame(chronic_flags, index=merged.index)
        merged = pd.concat([merged, chronic_frame], axis=1)

        chronic_flag_columns = list(chronic_frame.columns)
        merged["chronic_condition_count"] = (
            merged[chronic_flag_columns].fillna(False).astype(int).sum(axis=1)
        )
        merged["chronic_band"] = pd.cut(
            merged["chronic_condition_count"],
            bins=[-1, 0, 1, np.inf],
            labels=["无慢病", "1项慢病", "2项及以上"],
        )
        merged["chronic_band"] = merged["chronic_band"].astype("object").fillna("缺失")

        merged["PHQ9_total"] = merged[PHQ_ITEMS].sum(axis=1, min_count=len(PHQ_ITEMS))
        merged["PHQ9_high_risk"] = np.where(
            merged["PHQ9_total"].notna(),
            merged["PHQ9_total"] >= 10,
            np.nan,
        )
        merged["phq_severity_band"] = pd.cut(
            merged["PHQ9_total"],
            bins=[-np.inf, 4, 9, 14, 19, 27],
            labels=["最轻(0-4)", "轻度(5-9)", "中度(10-14)", "中重度(15-19)", "重度(20-27)"],
        )
        merged["phq_severity_band"] = merged["phq_severity_band"].astype("object").fillna("缺失")

        merged["short_sleep_flag"] = np.where(
            merged["weekday_sleep_hours"].notna(),
            merged["weekday_sleep_hours"] < 6,
            np.nan,
        )
        merged["long_sleep_flag"] = np.where(
            merged["weekday_sleep_hours"].notna(),
            merged["weekday_sleep_hours"] > 8,
            np.nan,
        )
        merged["low_income_flag"] = np.where(
            merged["INDFMPIR"].notna(),
            merged["INDFMPIR"] < 1.3,
            np.nan,
        )
        merged["obesity_flag"] = np.where(
            merged["BMXBMI"].notna(),
            merged["BMXBMI"] >= 30,
            np.nan,
        )
        merged["multi_chronic_flag"] = np.where(
            merged["chronic_condition_count"].notna(),
            merged["chronic_condition_count"] >= 2,
            np.nan,
        )

        priority_components = pd.DataFrame(
            {
                "phq_high_risk": merged["PHQ9_high_risk"],
                "short_sleep": merged["short_sleep_flag"],
                "low_income": merged["low_income_flag"],
                "obesity": merged["obesity_flag"],
                "multi_chronic": merged["multi_chronic_flag"],
            },
            index=merged.index,
        )
        merged["support_priority_score"] = (
            priority_components.fillna(False).astype(int).sum(axis=1)
        )
        merged["priority_tier"] = merged["support_priority_score"].map(PRIORITY_TIER_LABELS)
        merged["analysis_eligible"] = merged["PHQ9_total"].notna()

        return merged

    def _filtered_frame(
        self,
        min_age: int = 18,
        max_age: int = 80,
        require_phq: bool = False,
    ) -> pd.DataFrame:
        frame = self.phq_ready_frame.copy() if require_phq else self.analysis_frame.copy()
        filtered = frame[
            (frame["RIDAGEYR"].fillna(-1) >= min_age)
            & (frame["RIDAGEYR"].fillna(999) <= max_age)
        ]
        return filtered

    def _weighted_mean(self, frame: pd.DataFrame, value_column: str) -> float | None:
        valid = frame[[value_column, self.weight_column]].dropna()
        if valid.empty:
            return None
        weight_sum = float(valid[self.weight_column].sum())
        if weight_sum <= 0:
            return None
        return float(np.average(valid[value_column], weights=valid[self.weight_column]))

    def _weighted_series_rate(
        self, frame: pd.DataFrame, series: pd.Series
    ) -> float | None:
        valid = pd.DataFrame(
            {"value": series, self.weight_column: frame[self.weight_column]},
            index=frame.index,
        ).dropna()
        if valid.empty:
            return None
        weight_sum = float(valid[self.weight_column].sum())
        if weight_sum <= 0:
            return None
        return float(np.average(valid["value"].astype(float), weights=valid[self.weight_column]))

    def _weighted_rate_pct(self, frame: pd.DataFrame, value_column: str) -> float | None:
        rate = self._weighted_mean(frame, value_column)
        if rate is None:
            return None
        return rate * 100

    def _weighted_series_rate_pct(
        self, frame: pd.DataFrame, series: pd.Series
    ) -> float | None:
        rate = self._weighted_series_rate(frame, series)
        if rate is None:
            return None
        return rate * 100

    @staticmethod
    def _round(value: float | None, digits: int = 2) -> float | None:
        if value is None or pd.isna(value):
            return None
        return round(float(value), digits)

    def _overall_high_risk_rate(self, frame: pd.DataFrame | None = None) -> float | None:
        target_frame = self.phq_ready_frame if frame is None else frame
        return self._weighted_rate_pct(target_frame, "PHQ9_high_risk")

    def datasets_catalog(self) -> dict[str, Any]:
        files: list[dict[str, Any]] = []
        for dataset in self.datasets:
            frame = self.source_frames[dataset.filename]
            files.append(
                {
                    "file": dataset.filename,
                    "label": dataset.label,
                    "role": dataset.role,
                    "rows": int(len(frame)),
                    "columns": list(frame.columns),
                }
            )
        return {
            "cycle": "NHANES August 2021-August 2023",
            "files": files,
            "adult_demographics_rows": int(len(self.analysis_frame)),
            "phq_ready_rows": int(len(self.phq_ready_frame)),
            "join_key": "SEQN",
            "target_label": "PHQ9_high_risk",
        }

    def capabilities(self) -> dict[str, Any]:
        return {
            "service": "HealthInsight API",
            "version": "2.0.0",
            "style": {
                "base_path": "/api/v1",
                "docs": "/docs",
                "openapi": "/api/v1/openapi.json",
            },
            "current_modules": [
                "PHQ-9 风险标签构建",
                "心理健康风险画像",
                "高风险组合识别",
                "阈值模拟与资源估算",
                "多角色简报输出",
                "风险因素线索整理",
            ],
            "deferred_modules": [
                {
                    "name": "预测模型与校准",
                    "blocked_by": "当前版本以 PHQ-9 真实筛查标签为主，尚未加入单独的概率预测模型。",
                },
                {
                    "name": "公平性审计",
                    "blocked_by": "需要在后续版本中增加模型输出、分组阈值和更系统的误差分析。",
                },
                {
                    "name": "干预收益模拟",
                    "blocked_by": "需要引入更多随访或结局数据，才能支持更强的干预效果评估。",
                },
            ],
            "data_contract": {
                "resource_shape": [
                    "datasets",
                    "summary",
                    "population-profile",
                    "priority-cohorts",
                    "risk-factors",
                    "threshold-simulate",
                    "reports",
                ],
                "notes": [
                    "当前版本以 2021-2023 NHANES 公开成人样本为主。",
                    "高风险标签表示 PHQ-9 筛查阳性风险，不等同于临床诊断。",
                ],
            },
        }

    def summary(self) -> dict[str, Any]:
        frame = self.analysis_frame
        phq_ready = self.phq_ready_frame
        high_risk_rate = self._weighted_rate_pct(phq_ready, "PHQ9_high_risk")
        moderate_or_above = self._weighted_series_rate_pct(
            phq_ready, phq_ready["PHQ9_total"] >= 10
        )
        severe_or_above = self._weighted_series_rate_pct(
            phq_ready, phq_ready["PHQ9_total"] >= 20
        )
        priority_rate = self._weighted_series_rate_pct(
            phq_ready, phq_ready["support_priority_score"] >= 3
        )

        return {
            "cycle": "NHANES August 2021-August 2023",
            "sample": {
                "demographics_rows": int(len(self.source_frames["DEMO_L.xpt"])),
                "phq_rows": int(len(self.source_frames["DPQ_L.xpt"])),
                "sleep_rows": int(len(self.source_frames["SLQ_L.xpt"])),
                "body_measure_rows": int(len(self.source_frames["BMX_L.xpt"])),
                "medical_condition_rows": int(len(self.source_frames["MCQ_L.xpt"])),
                "merged_adult_rows": int(len(frame)),
                "phq_complete_rows": int(len(phq_ready)),
                "weighted_population_estimate": self._round(self.total_weight, 0),
            },
            "coverage": {
                "phq_complete_pct": self._round(frame["PHQ9_total"].notna().mean() * 100),
                "weekday_sleep_hours_pct": self._round(
                    frame["weekday_sleep_hours"].notna().mean() * 100
                ),
                "bmi_pct": self._round(frame["BMXBMI"].notna().mean() * 100),
                "income_ratio_pct": self._round(frame["INDFMPIR"].notna().mean() * 100),
                "chronic_question_pct": self._round(
                    frame["MCQ160A"].notna().mean() * 100
                ),
            },
            "mental_health_signals": {
                "mean_phq9_score": self._round(self._weighted_mean(phq_ready, "PHQ9_total")),
                "phq_high_risk_rate_pct": self._round(high_risk_rate),
                "moderate_or_above_rate_pct": self._round(moderate_or_above),
                "severe_rate_pct": self._round(severe_or_above),
            },
            "behavioral_signals": {
                "short_sleep_rate_pct": self._round(
                    self._weighted_rate_pct(frame, "short_sleep_flag")
                ),
                "long_sleep_rate_pct": self._round(
                    self._weighted_rate_pct(frame, "long_sleep_flag")
                ),
                "obesity_rate_pct": self._round(
                    self._weighted_rate_pct(frame, "obesity_flag")
                ),
                "multi_chronic_rate_pct": self._round(
                    self._weighted_rate_pct(frame, "multi_chronic_flag")
                ),
                "elevated_priority_rate_pct": self._round(priority_rate),
                "high_risk_rate_pct": self._round(high_risk_rate),
            },
            "threshold_reference": self.threshold_simulation(threshold=10, weekly_capacity=20),
            "current_boundary": {
                "supported": [
                    "PHQ-9 高风险标签构建",
                    "按收入、睡眠、BMI、教育与慢病的人群风险分层",
                    "阈值模拟与初步资源估算",
                    "面向机构角色的叙述性简报",
                ],
                "not_supported_yet": [
                    "个体临床诊断",
                    "基于独立预测模型的校准曲线",
                    "系统化公平性评估与阈值分组优化",
                ],
                "next_required_file": "如果继续做长期预测，下一步更适合补充更多共变量或随访结局数据。",
            },
        }

    def population_profile(
        self,
        group_by: str,
        min_age: int = 18,
        max_age: int = 80,
        min_participants: int = 50,
    ) -> dict[str, Any]:
        if group_by not in GROUP_FIELDS:
            raise ValueError(
                f"group_by must be one of: {', '.join(sorted(GROUP_FIELDS))}"
            )

        frame = self._filtered_frame(min_age=min_age, max_age=max_age, require_phq=False)
        filtered_total_weight = float(frame[self.weight_column].dropna().sum())
        rows: list[dict[str, Any]] = []

        for group_value, subset in frame.groupby(group_by, dropna=False):
            if len(subset) < min_participants:
                continue

            phq_subset = subset[subset["PHQ9_total"].notna()].copy()
            subset_weight = float(subset[self.weight_column].dropna().sum())
            weighted_share = (
                subset_weight / filtered_total_weight * 100 if filtered_total_weight > 0 else None
            )
            high_risk_rate = self._weighted_rate_pct(phq_subset, "PHQ9_high_risk")

            rows.append(
                {
                    "group": "未知" if pd.isna(group_value) else str(group_value),
                    "participants": int(len(subset)),
                    "eligible_participants": int(len(phq_subset)),
                    "weighted_share_pct": self._round(weighted_share),
                    "phq_complete_pct": self._round(
                        phq_subset.shape[0] / subset.shape[0] * 100 if len(subset) else None
                    ),
                    "mean_phq9_score": self._round(
                        self._weighted_mean(phq_subset, "PHQ9_total")
                    ),
                    "high_risk_rate_pct": self._round(high_risk_rate),
                    "elevated_priority_rate_pct": self._round(high_risk_rate),
                    "avg_weekday_sleep_hours": self._round(
                        self._weighted_mean(subset, "weekday_sleep_hours")
                    ),
                    "avg_bmi": self._round(self._weighted_mean(subset, "BMXBMI")),
                    "mean_chronic_condition_count": self._round(
                        self._weighted_mean(subset, "chronic_condition_count")
                    ),
                    "short_sleep_rate_pct": self._round(
                        self._weighted_rate_pct(subset, "short_sleep_flag")
                    ),
                    "multi_chronic_rate_pct": self._round(
                        self._weighted_rate_pct(subset, "multi_chronic_flag")
                    ),
                }
            )

        rows.sort(key=lambda item: item["high_risk_rate_pct"] or 0, reverse=True)
        return {
            "group_by": group_by,
            "filters": {
                "min_age": min_age,
                "max_age": max_age,
                "min_participants": min_participants,
            },
            "rows": rows,
        }

    def priority_cohorts(self, limit: int = 8, min_participants: int = 80) -> dict[str, Any]:
        frame = self._filtered_frame(require_phq=True)
        overall_rate = self._overall_high_risk_rate(frame) or 0.0

        grouped_rows: list[dict[str, Any]] = []
        for group_values, subset in frame.groupby(
            ["age_band", "income_band", "sleep_band"], dropna=False
        ):
            if len(subset) < min_participants:
                continue
            age_band, income_band, sleep_band = group_values
            high_risk_rate = self._weighted_rate_pct(subset, "PHQ9_high_risk")
            grouped_rows.append(
                {
                    "age_band": str(age_band),
                    "income_band": str(income_band),
                    "sleep_band": str(sleep_band),
                    "segment_label": f"{age_band} / {income_band} / {sleep_band}",
                    "participants": int(len(subset)),
                    "mean_phq9_score": self._round(
                        self._weighted_mean(subset, "PHQ9_total")
                    ),
                    "high_risk_rate_pct": self._round(high_risk_rate),
                    "elevated_priority_rate_pct": self._round(high_risk_rate),
                    "short_sleep_rate_pct": self._round(
                        self._weighted_rate_pct(subset, "short_sleep_flag")
                    ),
                    "multi_chronic_rate_pct": self._round(
                        self._weighted_rate_pct(subset, "multi_chronic_flag")
                    ),
                    "uplift_vs_overall_pct_point": self._round(
                        high_risk_rate - overall_rate if high_risk_rate is not None else None
                    ),
                }
            )

        rows = sorted(
            grouped_rows,
            key=lambda item: (
                item["high_risk_rate_pct"] or 0,
                item["mean_phq9_score"] or 0,
                item["participants"],
            ),
            reverse=True,
        )[:limit]

        return {
            "definition": "高优先组合以 PHQ-9 高风险比例为核心，同时参考睡眠不足、收入压力和慢病负担。",
            "rows": rows,
        }

    def risk_patterns(self, limit: int = 6, min_participants: int = 60) -> dict[str, Any]:
        rows = self.priority_cohorts(limit=limit, min_participants=min_participants)["rows"]
        return {
            "definition": "风险组合用于发现同时具备年龄、收入与睡眠压力的人群模式。",
            "rows": rows,
        }

    def risk_factors(self, limit: int = 8, min_participants: int = 120) -> dict[str, Any]:
        frame = self._filtered_frame(require_phq=True)
        overall_rate = self._overall_high_risk_rate(frame) or 0.0
        rows: list[dict[str, Any]] = []
        dimensions = [
            ("收入层", "income_band"),
            ("睡眠分层", "sleep_band"),
            ("BMI 分层", "bmi_band"),
            ("教育层", "education_band"),
            ("慢病负担", "chronic_band"),
            ("年龄层", "age_band"),
            ("性别", "gender"),
            ("族裔", "race_ethnicity"),
        ]

        for dimension_label, field in dimensions:
            for group_value, subset in frame.groupby(field, dropna=False):
                if len(subset) < min_participants:
                    continue
                group_name = "未知" if pd.isna(group_value) else str(group_value)
                if group_name in {"未知", "缺失"}:
                    continue
                high_risk_rate = self._weighted_rate_pct(subset, "PHQ9_high_risk")
                if high_risk_rate is None:
                    continue
                rows.append(
                    {
                        "dimension": dimension_label,
                        "group": group_name,
                        "participants": int(len(subset)),
                        "mean_phq9_score": self._round(
                            self._weighted_mean(subset, "PHQ9_total")
                        ),
                        "high_risk_rate_pct": self._round(high_risk_rate),
                        "uplift_vs_overall_pct_point": self._round(high_risk_rate - overall_rate),
                    }
                )

        rows.sort(
            key=lambda item: (
                item["uplift_vs_overall_pct_point"] or 0,
                item["high_risk_rate_pct"] or 0,
                item["participants"],
            ),
            reverse=True,
        )
        return {
            "overall_high_risk_rate_pct": self._round(overall_rate),
            "rows": rows[:limit],
        }

    def threshold_simulation(
        self, threshold: int = 10, weekly_capacity: int = 20
    ) -> dict[str, Any]:
        if threshold < 0 or threshold > 27:
            raise ValueError("threshold must be between 0 and 27")
        if weekly_capacity < 1 or weekly_capacity > 10000:
            raise ValueError("weekly_capacity must be between 1 and 10000")

        frame = self._filtered_frame(require_phq=True)
        flagged = frame["PHQ9_total"] >= threshold
        baseline = frame["PHQ9_total"] >= 10

        weighted_flagged_pct = self._weighted_series_rate_pct(frame, flagged)
        weighted_baseline_pct = self._weighted_series_rate_pct(frame, baseline)
        flagged_n = int(flagged.sum())
        baseline_n = int(baseline.sum())
        mean_flagged_score = self._weighted_mean(frame[flagged], "PHQ9_total")
        counselor_weeks = math.ceil(flagged_n / weekly_capacity) if flagged_n else 0

        if threshold <= 8:
            recommendation = "更敏感的筛查设置，适合希望优先减少漏筛的场景。"
        elif threshold <= 12:
            recommendation = "相对平衡的筛查设置，适合常规机构级筛查或初步转介。"
        else:
            recommendation = "更保守的筛查设置，适合资源有限、需要控制转介量的场景。"

        return {
            "threshold": threshold,
            "weekly_capacity": weekly_capacity,
            "flagged_n": flagged_n,
            "flagged_weighted_pct": self._round(weighted_flagged_pct),
            "mean_flagged_phq9_score": self._round(mean_flagged_score),
            "delta_vs_threshold_10_pct_point": self._round(
                (weighted_flagged_pct or 0) - (weighted_baseline_pct or 0)
            ),
            "delta_vs_threshold_10_n": flagged_n - baseline_n,
            "estimated_counselor_weeks": counselor_weeks,
            "recommended_use": recommendation,
        }

    def audience_report(self, audience: str) -> dict[str, Any]:
        audience = audience.lower()
        supported = {"researcher", "manager", "clinical", "engineering"}
        if audience not in supported:
            raise ValueError(f"audience must be one of: {', '.join(sorted(supported))}")

        top_cohorts = self.priority_cohorts(limit=3, min_participants=80)["rows"]
        summary = self.summary()
        risk_factors = self.risk_factors(limit=3, min_participants=120)["rows"]
        high_risk = summary["mental_health_signals"]["phq_high_risk_rate_pct"]
        mean_phq = summary["mental_health_signals"]["mean_phq9_score"]

        shared_notes = [
            "当前结果基于 NHANES 2021-2023 成人公开样本。",
            "PHQ-9 高风险标签表示筛查阳性风险，不等同于正式临床诊断。",
            "平台适合群体洞察、服务规划和机构级沟通，不替代医生或心理咨询师判断。",
        ]

        if audience == "researcher":
            headline = "面向研究团队的 PHQ-9 心理健康风险画像与分层差异摘要。"
            focus = [
                f"当前加权 PHQ-9 高风险比例约为 {high_risk}%，加权平均 PHQ-9 总分约为 {mean_phq}。",
                "收入分层、睡眠分层和慢病负担分层都能观察到较明显的风险差异。",
                "适合据此继续开展变量关系、机制假设和亚群比较分析。",
            ]
        elif audience == "manager":
            headline = "面向管理团队的高风险群体识别与筛查资源配置摘要。"
            focus = [
                "可优先把筛查与外展资源投向低收入、睡眠不足或慢病负担更高的群体。",
                "阈值模拟可帮助估算不同筛查策略下的转介量和人力承接压力。",
                "建议把平台作为筛查运营与资源配置的辅助工具，而不是个体诊断工具。",
            ]
        elif audience == "clinical":
            headline = "面向临床团队的 PHQ-9 初筛支持与重点关注对象摘要。"
            focus = [
                "PHQ-9 高风险结果适合作为进一步访谈、复核和转介的筛查信号。",
                "睡眠不足、慢病共病和经济压力可作为临床沟通中的背景风险线索。",
                "阈值设置可按场景调整，以平衡漏筛风险和转介承载能力。",
            ]
        else:
            headline = "面向技术团队的数据接入、指标复用与产品扩展摘要。"
            focus = [
                "当前平台已具备 PHQ-9 标签构建、画像分层、阈值模拟和角色简报能力。",
                "后续可继续扩展公平性检查、上传分析和报告导出模块。",
                "所有接口都围绕同一份清洗后的 NHANES 分析框架构建，便于多端复用。",
            ]

        return {
            "audience": audience,
            "headline": headline,
            "focus_points": focus,
            "top_cohorts": top_cohorts,
            "top_risk_factors": risk_factors,
            "shared_notes": shared_notes,
        }

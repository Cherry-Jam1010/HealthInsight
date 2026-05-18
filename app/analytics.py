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

CURRENT_GROUP_FIELDS = {
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
SHARED_GROUP_FIELDS = {
    "age_band",
    "gender",
    "race_ethnicity",
    "income_band",
    "education_band",
    "sleep_band",
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
CURRENT_CHRONIC_CONDITION_LABELS = {
    "MCQ160A": "关节炎",
    "MCQ160B": "充血性心力衰竭",
    "MCQ160C": "冠心病",
    "MCQ160D": "心绞痛",
    "MCQ160E": "心肌梗死",
    "MCQ160F": "中风",
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
    4: "优先转介",
    5: "优先转介",
}
LEGACY_ACTIVITY_YES_NO_COLUMNS = [
    "PAQ605",
    "PAQ620",
    "PAQ635",
    "PAQ650",
    "PAQ665",
]
DEFAULT_MENTAL_DATA_BASE_URL = os.getenv(
    "HEALTHINSIGHT_MH_DATA_BASE_URL",
    "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles",
)
DEFAULT_LEGACY_DATA_BASE_URL = os.getenv(
    "HEALTHINSIGHT_LEGACY_DATA_BASE_URL",
    "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles",
)


@dataclass(frozen=True)
class DatasetInfo:
    filename: str
    label: str
    role: str
    source: str


class NHANESAnalyticsService:
    """Dual-source analytics service.

    - NHANES/: current mental-health analytics built around PHQ-9.
    - data/: legacy behavior baseline used for historical context.
    """

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.current_data_dir = project_dir / "NHANES"
        self.legacy_data_dir = project_dir / "data"
        self.current_weight_column = "WTMEC2YR"
        self.legacy_weight_column = "WTMECPRP"

        self.current_datasets = [
            DatasetInfo(
                "DEMO_L.xpt",
                "人口学",
                "年龄、性别、教育、收入与权重",
                "current",
            ),
            DatasetInfo(
                "DPQ_L.xpt",
                "PHQ-9 抑郁筛查",
                "构建 PHQ-9 总分与高风险标签",
                "current",
            ),
            DatasetInfo(
                "SLQ_L.xpt",
                "睡眠",
                "构建睡眠时长与短睡眠分层",
                "current",
            ),
            DatasetInfo(
                "BMX_L.xpt",
                "身体测量",
                "构建 BMI 分层",
                "current",
            ),
            DatasetInfo(
                "MCQ_L.xpt",
                "慢病状况",
                "构建慢病负担与共病信号",
                "current",
            ),
        ]
        self.legacy_datasets = [
            DatasetInfo(
                "P_DEMO.xpt",
                "历史人口学基线",
                "用于历史样本结构、收入与教育背景",
                "legacy",
            ),
            DatasetInfo(
                "P_SLQ.xpt",
                "历史睡眠基线",
                "用于历史短睡眠与睡眠时长背景",
                "legacy",
            ),
            DatasetInfo(
                "P_PAQ.xpt",
                "历史活动基线",
                "用于历史活动参与与久坐背景",
                "legacy",
            ),
        ]

        self._ensure_current_files()
        self._ensure_legacy_files()

        self.current_source_frames = {
            info.filename: self._load_xpt(self.current_data_dir / info.filename)
            for info in self.current_datasets
        }
        self.legacy_source_frames = {
            info.filename: self._load_xpt(self.legacy_data_dir / info.filename)
            for info in self.legacy_datasets
        }

        self.analysis_frame = self._prepare_current_analysis_frame()
        self.phq_ready_frame = self.analysis_frame[
            self.analysis_frame["PHQ9_total"].notna()
        ].copy()
        self.legacy_frame = self._prepare_legacy_analysis_frame()

        self.current_total_weight = float(
            self.analysis_frame[self.current_weight_column].dropna().sum()
        )
        self.current_phq_ready_weight = float(
            self.phq_ready_frame[self.current_weight_column].dropna().sum()
        )
        self.legacy_total_weight = float(
            self.legacy_frame[self.legacy_weight_column].dropna().sum()
        )

    def _ensure_current_files(self) -> None:
        self.current_data_dir.mkdir(parents=True, exist_ok=True)
        missing = [
            dataset.filename
            for dataset in self.current_datasets
            if not (self.current_data_dir / dataset.filename).exists()
        ]
        if not missing:
            return

        base_url = DEFAULT_MENTAL_DATA_BASE_URL.rstrip("/")
        for filename in missing:
            self._download_data_file(base_url, filename, self.current_data_dir)

    def _ensure_legacy_files(self) -> None:
        self.legacy_data_dir.mkdir(parents=True, exist_ok=True)
        missing = [
            dataset.filename
            for dataset in self.legacy_datasets
            if not (self.legacy_data_dir / dataset.filename).exists()
        ]
        if not missing:
            return

        base_url = DEFAULT_LEGACY_DATA_BASE_URL.rstrip("/")
        for filename in missing:
            self._download_data_file(base_url, filename, self.legacy_data_dir)

    def _download_data_file(self, base_url: str, filename: str, target_dir: Path) -> None:
        target_path = target_dir / filename
        temp_path = target_dir / f"{filename}.part"
        file_url = f"{base_url}/{filename}"

        try:
            with urlopen(file_url, timeout=120) as response, temp_path.open("wb") as output:
                shutil.copyfileobj(response, output)
            temp_path.replace(target_path)
        except (OSError, URLError) as exc:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(
                f"缺少数据文件 {filename}，并且自动下载失败。请检查 {file_url} 是否可访问，"
                f"或手动放入 {target_dir.name} 目录。"
            ) from exc

    def _load_xpt(self, path: Path) -> pd.DataFrame:
        frame = pd.read_sas(path, format="xport", encoding="utf-8")
        return self._clean_frame(frame)

    def _clean_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        cleaned = frame.copy()
        for column in cleaned.columns:
            series = cleaned[column]
            if pd.api.types.is_numeric_dtype(series):
                numeric_series = series.astype(float)
                numeric_series = numeric_series.mask(numeric_series.abs() < 1e-70, 0.0)
                cleaned[column] = numeric_series.replace(NUMERIC_SENTINELS, np.nan)
            else:
                cleaned[column] = series.replace(list(TEXT_SENTINELS), np.nan)
        return cleaned

    def _prepare_current_analysis_frame(self) -> pd.DataFrame:
        demo = self.current_source_frames["DEMO_L.xpt"].copy()
        dpq = self.current_source_frames["DPQ_L.xpt"].copy()
        slq = self.current_source_frames["SLQ_L.xpt"].copy()
        bmx = self.current_source_frames["BMX_L.xpt"].copy()
        mcq = self.current_source_frames["MCQ_L.xpt"].copy()

        adults = demo[demo["RIDAGEYR"].fillna(-1) >= 18].copy()
        merged = (
            adults.merge(dpq, on="SEQN", how="left")
            .merge(slq, on="SEQN", how="left")
            .merge(bmx, on="SEQN", how="left")
            .merge(mcq, on="SEQN", how="left")
        )

        self._apply_shared_demographic_bands(merged)
        self._apply_shared_sleep_bands(merged)
        self._apply_current_specific_features(merged)
        return merged

    def _prepare_legacy_analysis_frame(self) -> pd.DataFrame:
        demo = self.legacy_source_frames["P_DEMO.xpt"].copy()
        slq = self.legacy_source_frames["P_SLQ.xpt"].copy()
        paq = self.legacy_source_frames["P_PAQ.xpt"].copy()

        adults = demo[demo["RIDAGEYR"].fillna(-1) >= 18].copy()
        merged = adults.merge(slq, on="SEQN", how="left").merge(paq, on="SEQN", how="left")

        self._apply_shared_demographic_bands(merged)
        self._apply_shared_sleep_bands(merged)

        merged["low_income_flag"] = np.where(
            merged["INDFMPIR"].notna(),
            merged["INDFMPIR"] < 1.3,
            np.nan,
        )

        activity_answer_count = merged[LEGACY_ACTIVITY_YES_NO_COLUMNS].notna().sum(axis=1)
        activity_yes_count = (
            merged[LEGACY_ACTIVITY_YES_NO_COLUMNS].fillna(2).eq(1).sum(axis=1)
        )
        merged["activity_domain_count"] = np.where(
            activity_answer_count > 0,
            activity_yes_count,
            np.nan,
        )
        merged["any_activity_flag"] = np.where(
            activity_answer_count > 0,
            activity_yes_count > 0,
            np.nan,
        )
        merged["inactive_flag"] = np.where(
            activity_answer_count > 0,
            activity_yes_count == 0,
            np.nan,
        )
        merged["recreation_activity_flag"] = np.where(
            merged[["PAQ650", "PAQ665"]].notna().any(axis=1),
            merged[["PAQ650", "PAQ665"]].fillna(2).eq(1).any(axis=1),
            np.nan,
        )

        return merged

    def _apply_shared_demographic_bands(self, frame: pd.DataFrame) -> None:
        frame["gender"] = frame["RIAGENDR"].map(GENDER_LABELS).fillna("未知")
        frame["race_ethnicity"] = (
            frame["RIDRETH3"].map(RACE_ETHNICITY_LABELS).fillna("未知")
        )
        frame["education_band"] = (
            frame["DMDEDUC2"].map(EDUCATION_LABELS).fillna("缺失")
        )
        frame["age_band"] = pd.cut(
            frame["RIDAGEYR"],
            bins=[17, 24, 34, 49, 64, np.inf],
            labels=["18-24", "25-34", "35-49", "50-64", "65+"],
        )
        frame["age_band"] = frame["age_band"].astype("object").fillna("未知")
        frame["income_band"] = pd.cut(
            frame["INDFMPIR"],
            bins=[-np.inf, 1.3, 3.5, np.inf],
            labels=["低收入", "中等收入", "较高收入"],
        )
        frame["income_band"] = frame["income_band"].astype("object").fillna("缺失")

    def _apply_shared_sleep_bands(self, frame: pd.DataFrame) -> None:
        frame["weekday_sleep_hours"] = frame.get("SLD012")
        frame["weekend_sleep_hours"] = frame.get("SLD013")
        frame["sleep_gap_hours"] = (
            frame["weekend_sleep_hours"] - frame["weekday_sleep_hours"]
        )
        frame["sleep_band"] = pd.cut(
            frame["weekday_sleep_hours"],
            bins=[-np.inf, 6, 8, np.inf],
            labels=["睡眠不足(<6h)", "正常睡眠(6-8h)", "睡眠偏长(>8h)"],
        )
        frame["sleep_band"] = frame["sleep_band"].astype("object").fillna("缺失")
        frame["short_sleep_flag"] = np.where(
            frame["weekday_sleep_hours"].notna(),
            frame["weekday_sleep_hours"] < 6,
            np.nan,
        )
        frame["long_sleep_flag"] = np.where(
            frame["weekday_sleep_hours"].notna(),
            frame["weekday_sleep_hours"] > 8,
            np.nan,
        )

    def _apply_current_specific_features(self, frame: pd.DataFrame) -> None:
        frame["BMXBMI"] = frame["BMXBMI"].astype(float)
        frame["bmi_band"] = pd.cut(
            frame["BMXBMI"],
            bins=[-np.inf, 18.5, 25, 30, np.inf],
            labels=["偏瘦", "正常", "超重", "肥胖"],
        )
        frame["bmi_band"] = frame["bmi_band"].astype("object").fillna("缺失")

        chronic_flags: dict[str, pd.Series] = {}
        for column in CURRENT_CHRONIC_CONDITION_LABELS:
            chronic_flags[f"{column}_flag"] = np.where(
                frame[column].notna(),
                frame[column] == 1,
                np.nan,
            )
        chronic_frame = pd.DataFrame(chronic_flags, index=frame.index)
        frame[chronic_frame.columns] = chronic_frame

        chronic_flag_columns = list(chronic_frame.columns)
        frame["chronic_condition_count"] = (
            frame[chronic_flag_columns].fillna(False).astype(int).sum(axis=1)
        )
        frame["chronic_band"] = pd.cut(
            frame["chronic_condition_count"],
            bins=[-1, 0, 1, np.inf],
            labels=["无慢病", "1项慢病", "2项及以上"],
        )
        frame["chronic_band"] = frame["chronic_band"].astype("object").fillna("缺失")

        frame["PHQ9_total"] = frame[PHQ_ITEMS].sum(axis=1, min_count=len(PHQ_ITEMS))
        frame["PHQ9_high_risk"] = np.where(
            frame["PHQ9_total"].notna(),
            frame["PHQ9_total"] >= 10,
            np.nan,
        )
        frame["phq_severity_band"] = pd.cut(
            frame["PHQ9_total"],
            bins=[-np.inf, 4, 9, 14, 19, 27],
            labels=[
                "最轻(0-4)",
                "轻度(5-9)",
                "中度(10-14)",
                "中重度(15-19)",
                "重度(20-27)",
            ],
        )
        frame["phq_severity_band"] = (
            frame["phq_severity_band"].astype("object").fillna("缺失")
        )

        frame["low_income_flag"] = np.where(
            frame["INDFMPIR"].notna(),
            frame["INDFMPIR"] < 1.3,
            np.nan,
        )
        frame["obesity_flag"] = np.where(
            frame["BMXBMI"].notna(),
            frame["BMXBMI"] >= 30,
            np.nan,
        )
        frame["multi_chronic_flag"] = np.where(
            frame["chronic_condition_count"].notna(),
            frame["chronic_condition_count"] >= 2,
            np.nan,
        )

        priority_components = pd.DataFrame(
            {
                "phq_high_risk": frame["PHQ9_high_risk"],
                "short_sleep": frame["short_sleep_flag"],
                "low_income": frame["low_income_flag"],
                "obesity": frame["obesity_flag"],
                "multi_chronic": frame["multi_chronic_flag"],
            },
            index=frame.index,
        )
        frame["support_priority_score"] = (
            priority_components.fillna(False).astype(int).sum(axis=1)
        )
        frame["priority_tier"] = frame["support_priority_score"].map(PRIORITY_TIER_LABELS)
        frame["analysis_eligible"] = frame["PHQ9_total"].notna()

    def _filtered_current_frame(
        self,
        min_age: int = 18,
        max_age: int = 80,
        require_phq: bool = False,
    ) -> pd.DataFrame:
        frame = self.phq_ready_frame if require_phq else self.analysis_frame
        return frame[
            (frame["RIDAGEYR"].fillna(-1) >= min_age)
            & (frame["RIDAGEYR"].fillna(999) <= max_age)
        ].copy()

    def _filtered_legacy_frame(
        self,
        min_age: int = 18,
        max_age: int = 80,
    ) -> pd.DataFrame:
        frame = self.legacy_frame
        return frame[
            (frame["RIDAGEYR"].fillna(-1) >= min_age)
            & (frame["RIDAGEYR"].fillna(999) <= max_age)
        ].copy()

    def _weighted_mean(
        self, frame: pd.DataFrame, value_column: str, weight_column: str
    ) -> float | None:
        valid = frame[[value_column, weight_column]].dropna()
        if valid.empty:
            return None
        weight_sum = float(valid[weight_column].sum())
        if weight_sum <= 0:
            return None
        return float(np.average(valid[value_column], weights=valid[weight_column]))

    def _weighted_series_rate(
        self,
        frame: pd.DataFrame,
        series: pd.Series,
        weight_column: str,
    ) -> float | None:
        valid = pd.DataFrame(
            {"value": series, weight_column: frame[weight_column]},
            index=frame.index,
        ).dropna()
        if valid.empty:
            return None
        weight_sum = float(valid[weight_column].sum())
        if weight_sum <= 0:
            return None
        return float(np.average(valid["value"].astype(float), weights=valid[weight_column]))

    def _weighted_rate_pct(
        self,
        frame: pd.DataFrame,
        value_column: str,
        weight_column: str,
    ) -> float | None:
        rate = self._weighted_mean(frame, value_column, weight_column)
        if rate is None:
            return None
        return rate * 100

    def _weighted_series_rate_pct(
        self,
        frame: pd.DataFrame,
        series: pd.Series,
        weight_column: str,
    ) -> float | None:
        rate = self._weighted_series_rate(frame, series, weight_column)
        if rate is None:
            return None
        return rate * 100

    @staticmethod
    def _round(value: float | None, digits: int = 2) -> float | None:
        if value is None or pd.isna(value):
            return None
        return round(float(value), digits)

    def _overall_high_risk_rate(self, frame: pd.DataFrame | None = None) -> float | None:
        target = self.phq_ready_frame if frame is None else frame
        return self._weighted_rate_pct(
            target,
            "PHQ9_high_risk",
            self.current_weight_column,
        )

    def _group_snapshot(
        self,
        frame: pd.DataFrame,
        group_by: str,
        weight_column: str,
        include_phq: bool,
        min_participants: int,
    ) -> dict[str, dict[str, Any]]:
        total_weight = float(frame[weight_column].dropna().sum())
        rows: dict[str, dict[str, Any]] = {}

        for group_value, subset in frame.groupby(group_by, dropna=False):
            if len(subset) < min_participants:
                continue
            label = "未知" if pd.isna(group_value) else str(group_value)
            weighted_share = (
                float(subset[weight_column].dropna().sum()) / total_weight * 100
                if total_weight > 0
                else None
            )
            snapshot = {
                "participants": int(len(subset)),
                "weighted_share_pct": self._round(weighted_share),
                "avg_weekday_sleep_hours": self._round(
                    self._weighted_mean(subset, "weekday_sleep_hours", weight_column)
                ),
                "short_sleep_rate_pct": self._round(
                    self._weighted_rate_pct(subset, "short_sleep_flag", weight_column)
                ),
            }
            if include_phq:
                phq_subset = subset[subset["PHQ9_total"].notna()].copy()
                snapshot.update(
                    {
                        "eligible_participants": int(len(phq_subset)),
                        "mean_phq9_score": self._round(
                            self._weighted_mean(
                                phq_subset,
                                "PHQ9_total",
                                self.current_weight_column,
                            )
                        ),
                        "high_risk_rate_pct": self._round(
                            self._weighted_rate_pct(
                                phq_subset,
                                "PHQ9_high_risk",
                                self.current_weight_column,
                            )
                        ),
                    }
                )
            else:
                snapshot.update(
                    {
                        "inactive_rate_pct": self._round(
                            self._weighted_rate_pct(
                                subset,
                                "inactive_flag",
                                self.legacy_weight_column,
                            )
                        ),
                        "any_activity_rate_pct": self._round(
                            self._weighted_rate_pct(
                                subset,
                                "any_activity_flag",
                                self.legacy_weight_column,
                            )
                        ),
                    }
                )
            rows[label] = snapshot

        return rows

    def datasets_catalog(self) -> dict[str, Any]:
        def build_files(
            datasets: list[DatasetInfo], source_frames: dict[str, pd.DataFrame]
        ) -> list[dict[str, Any]]:
            rows = []
            for dataset in datasets:
                frame = source_frames[dataset.filename]
                rows.append(
                    {
                        "file": dataset.filename,
                        "label": dataset.label,
                        "role": dataset.role,
                        "rows": int(len(frame)),
                        "columns": list(frame.columns),
                    }
                )
            return rows

        return {
            "service_mode": "dual-source",
            "current_cycle": {
                "label": "NHANES August 2021-August 2023",
                "join_key": "SEQN",
                "target_label": "PHQ9_high_risk",
                "files": build_files(self.current_datasets, self.current_source_frames),
                "adult_rows": int(len(self.analysis_frame)),
                "phq_ready_rows": int(len(self.phq_ready_frame)),
            },
            "legacy_cycle": {
                "label": "Legacy behavior baseline",
                "join_key": "SEQN",
                "target_label": "historical_behavior_baseline",
                "files": build_files(self.legacy_datasets, self.legacy_source_frames),
                "adult_rows": int(len(self.legacy_frame)),
            },
        }

    def capabilities(self) -> dict[str, Any]:
        return {
            "service": "HealthInsight API",
            "version": "2.1.0",
            "style": {
                "base_path": "/api/v1",
                "docs": "/docs",
                "openapi": "/api/v1/openapi.json",
            },
            "current_modules": [
                "PHQ-9 风险识别",
                "双数据源对照",
                "重点人群组合识别",
                "风险因素整理",
                "阈值模拟与资源估算",
                "多角色简报输出",
            ],
            "deferred_modules": [
                {
                    "name": "预测模型与校准",
                    "blocked_by": "当前版本以真实 PHQ-9 筛查标签为主，尚未接入独立预测概率模型。",
                },
                {
                    "name": "公平性审计",
                    "blocked_by": "后续需要模型输出、分组阈值与更系统的误差分析能力。",
                },
                {
                    "name": "干预效果评估",
                    "blocked_by": "需要接入更长期的随访或服务结局数据。",
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
                    "cycle-comparison",
                    "reports",
                ],
                "notes": [
                    "当前周期用于心理健康风险识别，历史基线用于睡眠与活动背景对照。",
                    "PHQ-9 高风险表示筛查阳性风险，不等同于临床诊断。",
                ],
            },
        }

    def summary(self) -> dict[str, Any]:
        current_frame = self.analysis_frame
        phq_ready = self.phq_ready_frame
        legacy_frame = self.legacy_frame

        high_risk_rate = self._weighted_rate_pct(
            phq_ready,
            "PHQ9_high_risk",
            self.current_weight_column,
        )
        baseline_reference = self.threshold_simulation(threshold=10, weekly_capacity=20)
        current_short_sleep = self._weighted_rate_pct(
            current_frame,
            "short_sleep_flag",
            self.current_weight_column,
        )
        legacy_short_sleep = self._weighted_rate_pct(
            legacy_frame,
            "short_sleep_flag",
            self.legacy_weight_column,
        )

        return {
            "service_mode": "dual-source",
            "current_cycle": {
                "label": "NHANES August 2021-August 2023",
                "adult_rows": int(len(current_frame)),
                "phq_complete_rows": int(len(phq_ready)),
                "weighted_population_estimate": self._round(self.current_total_weight, 0),
            },
            "legacy_cycle": {
                "label": "Legacy behavior baseline",
                "adult_rows": int(len(legacy_frame)),
                "weighted_population_estimate": self._round(self.legacy_total_weight, 0),
            },
            "sample": {
                "demographics_rows": int(len(self.current_source_frames["DEMO_L.xpt"])),
                "phq_rows": int(len(self.current_source_frames["DPQ_L.xpt"])),
                "sleep_rows": int(len(self.current_source_frames["SLQ_L.xpt"])),
                "body_measure_rows": int(len(self.current_source_frames["BMX_L.xpt"])),
                "medical_condition_rows": int(len(self.current_source_frames["MCQ_L.xpt"])),
                "merged_adult_rows": int(len(current_frame)),
                "phq_complete_rows": int(len(phq_ready)),
            },
            "coverage": {
                "phq_complete_pct": self._round(current_frame["PHQ9_total"].notna().mean() * 100),
                "weekday_sleep_hours_pct": self._round(
                    current_frame["weekday_sleep_hours"].notna().mean() * 100
                ),
                "bmi_pct": self._round(current_frame["BMXBMI"].notna().mean() * 100),
                "income_ratio_pct": self._round(current_frame["INDFMPIR"].notna().mean() * 100),
                "chronic_question_pct": self._round(current_frame["MCQ160A"].notna().mean() * 100),
            },
            "mental_health_signals": {
                "mean_phq9_score": self._round(
                    self._weighted_mean(phq_ready, "PHQ9_total", self.current_weight_column)
                ),
                "phq_high_risk_rate_pct": self._round(high_risk_rate),
                "severe_rate_pct": self._round(
                    self._weighted_series_rate_pct(
                        phq_ready,
                        phq_ready["PHQ9_total"] >= 20,
                        self.current_weight_column,
                    )
                ),
            },
            "baseline_behavior_signals": {
                "legacy_short_sleep_rate_pct": self._round(legacy_short_sleep),
                "legacy_any_activity_rate_pct": self._round(
                    self._weighted_rate_pct(
                        legacy_frame,
                        "any_activity_flag",
                        self.legacy_weight_column,
                    )
                ),
                "legacy_inactive_rate_pct": self._round(
                    self._weighted_rate_pct(
                        legacy_frame,
                        "inactive_flag",
                        self.legacy_weight_column,
                    )
                ),
            },
            "shared_signals": {
                "current_short_sleep_rate_pct": self._round(current_short_sleep),
                "legacy_short_sleep_rate_pct": self._round(legacy_short_sleep),
                "short_sleep_gap_pct_point": self._round(
                    None
                    if current_short_sleep is None or legacy_short_sleep is None
                    else current_short_sleep - legacy_short_sleep
                ),
                "current_avg_sleep_hours": self._round(
                    self._weighted_mean(
                        current_frame,
                        "weekday_sleep_hours",
                        self.current_weight_column,
                    )
                ),
                "legacy_avg_sleep_hours": self._round(
                    self._weighted_mean(
                        legacy_frame,
                        "weekday_sleep_hours",
                        self.legacy_weight_column,
                    )
                ),
            },
            "threshold_reference": baseline_reference,
            "current_boundary": {
                "supported": [
                    "机构级 PHQ-9 风险洞察",
                    "双周期睡眠与人群背景对照",
                    "阈值模拟与初步资源估算",
                    "面向管理、研究与临床团队的简报输出",
                ],
                "not_supported_yet": [
                    "个体临床诊断",
                    "跨地区泛化结论",
                    "基于独立预测模型的公平性审计",
                ],
            },
        }

    def population_profile(
        self,
        group_by: str,
        min_age: int = 18,
        max_age: int = 80,
        min_participants: int = 50,
    ) -> dict[str, Any]:
        if group_by not in CURRENT_GROUP_FIELDS:
            raise ValueError(
                f"group_by must be one of: {', '.join(sorted(CURRENT_GROUP_FIELDS))}"
            )

        frame = self._filtered_current_frame(
            min_age=min_age,
            max_age=max_age,
            require_phq=False,
        )
        filtered_total_weight = float(frame[self.current_weight_column].dropna().sum())
        rows: list[dict[str, Any]] = []

        for group_value, subset in frame.groupby(group_by, dropna=False):
            if len(subset) < min_participants:
                continue

            phq_subset = subset[subset["PHQ9_total"].notna()].copy()
            subset_weight = float(subset[self.current_weight_column].dropna().sum())
            weighted_share = (
                subset_weight / filtered_total_weight * 100
                if filtered_total_weight > 0
                else None
            )
            high_risk_rate = self._weighted_rate_pct(
                phq_subset,
                "PHQ9_high_risk",
                self.current_weight_column,
            )

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
                        self._weighted_mean(
                            phq_subset,
                            "PHQ9_total",
                            self.current_weight_column,
                        )
                    ),
                    "high_risk_rate_pct": self._round(high_risk_rate),
                    "avg_weekday_sleep_hours": self._round(
                        self._weighted_mean(
                            subset,
                            "weekday_sleep_hours",
                            self.current_weight_column,
                        )
                    ),
                    "avg_bmi": self._round(
                        self._weighted_mean(subset, "BMXBMI", self.current_weight_column)
                    ),
                    "mean_chronic_condition_count": self._round(
                        self._weighted_mean(
                            subset,
                            "chronic_condition_count",
                            self.current_weight_column,
                        )
                    ),
                    "short_sleep_rate_pct": self._round(
                        self._weighted_rate_pct(
                            subset,
                            "short_sleep_flag",
                            self.current_weight_column,
                        )
                    ),
                    "multi_chronic_rate_pct": self._round(
                        self._weighted_rate_pct(
                            subset,
                            "multi_chronic_flag",
                            self.current_weight_column,
                        )
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
        frame = self._filtered_current_frame(require_phq=True)
        overall_rate = self._overall_high_risk_rate(frame) or 0.0

        grouped_rows: list[dict[str, Any]] = []
        for group_values, subset in frame.groupby(
            ["age_band", "income_band", "sleep_band"],
            dropna=False,
        ):
            if len(subset) < min_participants:
                continue
            age_band, income_band, sleep_band = group_values
            high_risk_rate = self._weighted_rate_pct(
                subset,
                "PHQ9_high_risk",
                self.current_weight_column,
            )
            grouped_rows.append(
                {
                    "age_band": str(age_band),
                    "income_band": str(income_band),
                    "sleep_band": str(sleep_band),
                    "segment_label": f"{age_band} / {income_band} / {sleep_band}",
                    "participants": int(len(subset)),
                    "mean_phq9_score": self._round(
                        self._weighted_mean(
                            subset,
                            "PHQ9_total",
                            self.current_weight_column,
                        )
                    ),
                    "high_risk_rate_pct": self._round(high_risk_rate),
                    "short_sleep_rate_pct": self._round(
                        self._weighted_rate_pct(
                            subset,
                            "short_sleep_flag",
                            self.current_weight_column,
                        )
                    ),
                    "multi_chronic_rate_pct": self._round(
                        self._weighted_rate_pct(
                            subset,
                            "multi_chronic_flag",
                            self.current_weight_column,
                        )
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
            "definition": "重点组合以当前周期的 PHQ-9 高风险比例为核心，同时参考睡眠、收入与慢病负担。",
            "rows": rows,
        }

    def risk_patterns(self, limit: int = 6, min_participants: int = 60) -> dict[str, Any]:
        rows = self.priority_cohorts(limit=limit, min_participants=min_participants)["rows"]
        return {
            "definition": "风险模式用于快速发现同时承受年龄、收入与睡眠压力的人群组合。",
            "rows": rows,
        }

    def risk_factors(self, limit: int = 8, min_participants: int = 120) -> dict[str, Any]:
        frame = self._filtered_current_frame(require_phq=True)
        overall_rate = self._overall_high_risk_rate(frame) or 0.0
        rows: list[dict[str, Any]] = []
        dimensions = [
            ("收入层", "income_band"),
            ("睡眠层", "sleep_band"),
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
                high_risk_rate = self._weighted_rate_pct(
                    subset,
                    "PHQ9_high_risk",
                    self.current_weight_column,
                )
                if high_risk_rate is None:
                    continue
                rows.append(
                    {
                        "dimension": dimension_label,
                        "group": group_name,
                        "participants": int(len(subset)),
                        "mean_phq9_score": self._round(
                            self._weighted_mean(
                                subset,
                                "PHQ9_total",
                                self.current_weight_column,
                            )
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

    def cycle_comparison(
        self,
        group_by: str = "age_band",
        min_age: int = 18,
        max_age: int = 80,
        min_participants: int = 80,
    ) -> dict[str, Any]:
        if group_by not in SHARED_GROUP_FIELDS:
            raise ValueError(
                f"group_by must be one of: {', '.join(sorted(SHARED_GROUP_FIELDS))}"
            )

        current_frame = self._filtered_current_frame(
            min_age=min_age,
            max_age=max_age,
            require_phq=True,
        )
        legacy_frame = self._filtered_legacy_frame(min_age=min_age, max_age=max_age)

        current_rows = self._group_snapshot(
            current_frame,
            group_by,
            self.current_weight_column,
            include_phq=True,
            min_participants=min_participants,
        )
        legacy_rows = self._group_snapshot(
            legacy_frame,
            group_by,
            self.legacy_weight_column,
            include_phq=False,
            min_participants=min_participants,
        )

        merged_rows: list[dict[str, Any]] = []
        for label in sorted(set(current_rows) | set(legacy_rows)):
            current = current_rows.get(label, {})
            legacy = legacy_rows.get(label, {})
            current_short_sleep = current.get("short_sleep_rate_pct")
            legacy_short_sleep = legacy.get("short_sleep_rate_pct")
            merged_rows.append(
                {
                    "group": label,
                    "current_participants": current.get("participants"),
                    "baseline_participants": legacy.get("participants"),
                    "current_weighted_share_pct": current.get("weighted_share_pct"),
                    "baseline_weighted_share_pct": legacy.get("weighted_share_pct"),
                    "current_high_risk_rate_pct": current.get("high_risk_rate_pct"),
                    "current_mean_phq9_score": current.get("mean_phq9_score"),
                    "current_short_sleep_rate_pct": current_short_sleep,
                    "baseline_short_sleep_rate_pct": legacy_short_sleep,
                    "baseline_inactive_rate_pct": legacy.get("inactive_rate_pct"),
                    "current_avg_weekday_sleep_hours": current.get("avg_weekday_sleep_hours"),
                    "baseline_avg_weekday_sleep_hours": legacy.get("avg_weekday_sleep_hours"),
                    "short_sleep_gap_pct_point": self._round(
                        None
                        if current_short_sleep is None or legacy_short_sleep is None
                        else current_short_sleep - legacy_short_sleep
                    ),
                }
            )

        merged_rows.sort(
            key=lambda item: abs(item["short_sleep_gap_pct_point"] or 0),
            reverse=True,
        )
        return {
            "group_by": group_by,
            "filters": {
                "min_age": min_age,
                "max_age": max_age,
                "min_participants": min_participants,
            },
            "definition": "当前周期提供 PHQ-9 风险，历史周期提供睡眠与活动基线，用于同维度对照。",
            "rows": merged_rows,
        }

    def threshold_simulation(
        self,
        threshold: int = 10,
        weekly_capacity: int = 20,
    ) -> dict[str, Any]:
        if threshold < 0 or threshold > 27:
            raise ValueError("threshold must be between 0 and 27")
        if weekly_capacity < 1 or weekly_capacity > 10000:
            raise ValueError("weekly_capacity must be between 1 and 10000")

        frame = self._filtered_current_frame(require_phq=True)
        flagged = frame["PHQ9_total"] >= threshold
        baseline = frame["PHQ9_total"] >= 10

        weighted_flagged_pct = self._weighted_series_rate_pct(
            frame,
            flagged,
            self.current_weight_column,
        )
        weighted_baseline_pct = self._weighted_series_rate_pct(
            frame,
            baseline,
            self.current_weight_column,
        )
        flagged_n = int(flagged.sum())
        baseline_n = int(baseline.sum())
        mean_flagged_score = self._weighted_mean(
            frame[flagged],
            "PHQ9_total",
            self.current_weight_column,
        )
        counselor_weeks = math.ceil(flagged_n / weekly_capacity) if flagged_n else 0

        if threshold <= 8:
            recommendation = "更敏感的设置，适合优先减少漏筛。"
        elif threshold <= 12:
            recommendation = "更平衡的设置，适合常规筛查与初步转介。"
        else:
            recommendation = "更保守的设置，适合资源有限的场景。"

        return {
            "threshold": threshold,
            "weekly_capacity": weekly_capacity,
            "flagged_n": flagged_n,
            "flagged_weighted_pct": self._round(weighted_flagged_pct),
            "mean_flagged_phq9_score": self._round(mean_flagged_score),
            "delta_vs_threshold_10_pct_point": self._round(
                None
                if weighted_flagged_pct is None or weighted_baseline_pct is None
                else weighted_flagged_pct - weighted_baseline_pct
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
        current_short_sleep = summary["shared_signals"]["current_short_sleep_rate_pct"]
        legacy_short_sleep = summary["shared_signals"]["legacy_short_sleep_rate_pct"]

        shared_notes = [
            "当前结论基于 NHANES 2021-2023 成人样本的 PHQ-9 风险分析。",
            "历史基线来自旧周期行为样本，用于补充睡眠和活动背景。",
            "平台适合群体分析、筛查规划与机构汇报，不替代正式临床判断。",
        ]

        if audience == "researcher":
            headline = "研究视角：当前 PHQ-9 风险与历史行为基线的联合摘要"
            focus = [
                f"当前加权 PHQ-9 高风险比例约为 {high_risk}%，平均 PHQ-9 约为 {mean_phq}。",
                f"当前短睡眠约为 {current_short_sleep}%，历史基线约为 {legacy_short_sleep}%，可作为同维度背景。",
                "适合继续做收入、睡眠和慢病负担相关的分层与机制分析。",
            ]
        elif audience == "manager":
            headline = "管理视角：优先筛查谁、需要多少资源、应该先做什么"
            focus = [
                "优先把筛查与外展资源投向低收入、短睡眠和慢病负担更高的人群。",
                "当前周期负责识别 PHQ-9 风险，历史基线负责解释长期行为背景。",
                "阈值模拟可帮助估算不同策略下的转介量和承接压力。",
            ]
        elif audience == "clinical":
            headline = "临床视角：哪些群体更值得优先复核与进一步访谈"
            focus = [
                "PHQ-9 高风险结果适合作为后续访谈、复核和转介的筛查起点。",
                "短睡眠、经济压力与慢病负担可作为沟通时的背景线索。",
                "平台输出的是群体洞察，不替代医生或心理咨询师的最终判断。",
            ]
        else:
            headline = "技术视角：一个由双数据源驱动的心理健康洞察 API"
            focus = [
                "当前周期负责 PHQ-9 风险与阈值模拟，历史基线负责睡眠与活动背景。",
                "接口结构统一，适合前端站点、报告服务和后续模型模块复用。",
                "后续可在现有框架上继续接入公平性检查、导出和上传分析。",
            ]

        return {
            "audience": audience,
            "headline": headline,
            "focus_points": focus,
            "top_cohorts": top_cohorts,
            "top_risk_factors": risk_factors,
            "shared_notes": shared_notes,
        }

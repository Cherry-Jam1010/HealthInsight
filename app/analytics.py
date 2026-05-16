from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


NUMERIC_SENTINELS = [7, 9, 77, 99, 777, 999, 7777, 9999, 77777, 99999]
TEXT_SENTINELS = {"", "77777", "99999"}
GROUP_FIELDS = {
    "age_band",
    "gender",
    "race_ethnicity",
    "income_band",
    "priority_tier",
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

PRIORITY_TIER_LABELS = {
    0: "基础",
    1: "基础",
    2: "观察",
    3: "高优先级",
    4: "高优先级",
    5: "高优先级",
}


@dataclass(frozen=True)
class DatasetInfo:
    filename: str
    label: str
    role: str


class NHANESAnalyticsService:
    """Load, join, and summarize the NHANES 2017-March 2020 pre-pandemic files."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.datasets = [
            DatasetInfo("P_DEMO.xpt", "人口学", "人口学主表与访谈权重"),
            DatasetInfo("P_PAQ.xpt", "体力活动", "行为活动模式"),
            DatasetInfo("P_SLQ.xpt", "睡眠", "睡眠时长与睡眠相关筛查输入"),
        ]
        self.source_frames = {
            info.filename: self._load_xpt(info.filename) for info in self.datasets
        }
        self.analysis_frame = self._prepare_analysis_frame()
        self.total_weight = float(self.analysis_frame["WTINTPRP"].dropna().sum())

    def _load_xpt(self, filename: str) -> pd.DataFrame:
        frame = pd.read_sas(self.data_dir / filename, format="xport", encoding="utf-8")
        return self._clean_frame(frame)

    def _clean_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        cleaned = frame.copy()
        for column in cleaned.columns:
            series = cleaned[column]
            if pd.api.types.is_numeric_dtype(series):
                series = series.astype(float)
                series = series.mask(series.abs() < 1e-70, np.nan)
                cleaned[column] = series.replace(NUMERIC_SENTINELS, np.nan)
            else:
                cleaned[column] = series.replace(list(TEXT_SENTINELS), np.nan)
        return cleaned

    def _prepare_analysis_frame(self) -> pd.DataFrame:
        demo = self.source_frames["P_DEMO.xpt"].copy()
        paq = self.source_frames["P_PAQ.xpt"].copy()
        slq = self.source_frames["P_SLQ.xpt"].copy()
        merged = demo.merge(paq, on="SEQN", how="inner").merge(slq, on="SEQN", how="inner")

        merged["gender"] = merged["RIAGENDR"].map(GENDER_LABELS).fillna("未知")
        merged["race_ethnicity"] = (
            merged["RIDRETH3"].map(RACE_ETHNICITY_LABELS).fillna("未知")
        )

        merged["age_band"] = pd.cut(
            merged["RIDAGEYR"],
            bins=[17, 29, 44, 59, np.inf],
            labels=["18-29", "30-44", "45-59", "60+"],
        )
        merged["age_band"] = merged["age_band"].astype("object").fillna("未知")

        merged["income_band"] = pd.cut(
            merged["INDFMPIR"],
            bins=[-np.inf, 1, 2, 4, np.inf],
            labels=["<1.0", "1.0-1.99", "2.0-3.99", "4.0+"],
        )
        merged["income_band"] = merged["income_band"].astype("object").fillna("缺失")

        merged["weekday_sleep_hours"] = merged["SLD012"]
        merged["weekend_sleep_hours"] = merged["SLD013"]
        merged["sleep_gap_hours"] = merged["weekend_sleep_hours"] - merged["weekday_sleep_hours"]
        merged["sedentary_minutes_day"] = merged["PAD680"]
        merged["sedentary_hours_day"] = merged["sedentary_minutes_day"] / 60.0

        merged["recreation_vigorous"] = np.where(
            merged["PAQ650"].notna(), merged["PAQ650"] == 1, np.nan
        )
        merged["recreation_moderate"] = np.where(
            merged["PAQ665"].notna(), merged["PAQ665"] == 1, np.nan
        )
        merged["transport_active"] = np.where(
            merged["PAQ635"].notna(), merged["PAQ635"] == 1, np.nan
        )

        merged["short_sleep_flag"] = np.where(
            merged["weekday_sleep_hours"].notna(),
            merged["weekday_sleep_hours"] < 7,
            np.nan,
        )
        merged["high_sedentary_flag"] = np.where(
            merged["sedentary_minutes_day"].notna(),
            merged["sedentary_minutes_day"] >= 480,
            np.nan,
        )
        merged["sleep_gap_flag"] = np.where(
            merged["sleep_gap_hours"].notna(),
            merged["sleep_gap_hours"] >= 2,
            np.nan,
        )
        merged["low_income_flag"] = np.where(
            merged["INDFMPIR"].notna(), merged["INDFMPIR"] < 1, np.nan
        )
        recreation_known = merged["PAQ650"].notna() | merged["PAQ665"].notna()
        recreation_yes = (merged["PAQ650"] == 1) | (merged["PAQ665"] == 1)
        merged["low_recreation_flag"] = np.where(recreation_known, ~recreation_yes, np.nan)

        priority_flags = [
            "short_sleep_flag",
            "high_sedentary_flag",
            "sleep_gap_flag",
            "low_income_flag",
            "low_recreation_flag",
        ]
        merged["screening_priority_score"] = (
            merged[priority_flags].fillna(False).astype(int).sum(axis=1)
        )
        merged["priority_tier"] = merged["screening_priority_score"].map(
            PRIORITY_TIER_LABELS
        )
        return merged

    def _filtered_frame(self, min_age: int = 18, max_age: int = 80) -> pd.DataFrame:
        filtered = self.analysis_frame.copy()
        return filtered[
            (filtered["RIDAGEYR"].fillna(-1) >= min_age)
            & (filtered["RIDAGEYR"].fillna(999) <= max_age)
        ]

    def _weighted_mean(self, frame: pd.DataFrame, value_column: str) -> float | None:
        valid = frame[[value_column, "WTINTPRP"]].dropna()
        if valid.empty:
            return None
        weight_sum = float(valid["WTINTPRP"].sum())
        if weight_sum <= 0:
            return None
        return float(np.average(valid[value_column], weights=valid["WTINTPRP"]))

    def _weighted_rate(self, frame: pd.DataFrame, value_column: str) -> float | None:
        return self._weighted_mean(frame, value_column)

    def _weighted_series_rate(
        self, frame: pd.DataFrame, series: pd.Series
    ) -> float | None:
        valid = pd.DataFrame({"value": series, "WTINTPRP": frame["WTINTPRP"]}).dropna()
        if valid.empty:
            return None
        weight_sum = float(valid["WTINTPRP"].sum())
        if weight_sum <= 0:
            return None
        return float(np.average(valid["value"].astype(float), weights=valid["WTINTPRP"]))

    def _weighted_rate_pct(self, frame: pd.DataFrame, value_column: str) -> float | None:
        rate = self._weighted_rate(frame, value_column)
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
            "cycle": "NHANES 2017-March 2020 疫情前阶段",
            "files": files,
            "merged_rows": int(len(self.analysis_frame)),
            "join_key": "SEQN",
        }

    def capabilities(self) -> dict[str, Any]:
        return {
            "service": "HealthInsight API",
            "version": "1.0.0",
            "style": {
                "base_path": "/api/v1",
                "docs": "/docs",
                "openapi": "/api/v1/openapi.json",
            },
            "current_modules": [
                "数据集目录",
                "数据体检",
                "人群画像",
                "行为筛查优先级摘要",
                "面向角色的叙述性报告",
            ],
            "deferred_modules": [
                {
                    "name": "PHQ-9 风险建模",
                    "blocked_by": "当前仓库缺少 P_DPQ.xpt 或其他抑郁结局数据文件。",
                },
                {
                    "name": "公平性审计与阈值优化",
                    "blocked_by": "这些能力需要真实标签或模型分数，而不仅仅是协变量。",
                },
                {
                    "name": "因果调整与干预模拟",
                    "blocked_by": "需要 BMI、慢病、医疗可及性等更丰富的协变量模块。",
                },
            ],
            "data_contract": {
                "resource_shape": [
                    "datasets",
                    "summary",
                    "population-profile",
                    "priority-cohorts",
                    "reports",
                ],
                "notes": [
                    "当前 MVP 主要提供只读 GET 接口。",
                    "后续如加入上传数据或长任务分析，可扩展为 POST 任务型接口。",
                ],
            },
        }

    def summary(self) -> dict[str, Any]:
        frame = self.analysis_frame
        merged_rows = len(frame)
        watchlist_rate = self._weighted_series_rate(
            frame, frame["screening_priority_score"] >= 2
        )
        elevated_rate = self._weighted_series_rate(
            frame, frame["screening_priority_score"] >= 3
        )
        return {
            "cycle": "NHANES 2017-March 2020 疫情前阶段",
            "sample": {
                "demographics_rows": int(len(self.source_frames["P_DEMO.xpt"])),
                "physical_activity_rows": int(len(self.source_frames["P_PAQ.xpt"])),
                "sleep_rows": int(len(self.source_frames["P_SLQ.xpt"])),
                "merged_adult_rows": int(merged_rows),
                "weighted_population_estimate": self._round(self.total_weight, 0),
            },
            "coverage": {
                "weekday_sleep_hours_pct": self._round(
                    frame["weekday_sleep_hours"].notna().mean() * 100
                ),
                "weekend_sleep_hours_pct": self._round(
                    frame["weekend_sleep_hours"].notna().mean() * 100
                ),
                "sedentary_minutes_pct": self._round(
                    frame["sedentary_minutes_day"].notna().mean() * 100
                ),
                "income_ratio_pct": self._round(frame["INDFMPIR"].notna().mean() * 100),
            },
            "behavioral_signals": {
                "short_sleep_rate_pct": self._round(
                    self._weighted_rate_pct(frame, "short_sleep_flag")
                ),
                "high_sedentary_rate_pct": self._round(
                    self._weighted_rate_pct(frame, "high_sedentary_flag")
                ),
                "low_recreation_rate_pct": self._round(
                    self._weighted_rate_pct(frame, "low_recreation_flag")
                ),
                "watchlist_or_elevated_rate_pct": self._round(
                    watchlist_rate * 100 if watchlist_rate is not None else None
                ),
                "elevated_rate_pct": self._round(
                    elevated_rate * 100 if elevated_rate is not None else None
                ),
            },
            "current_boundary": {
                "supported": [
                    "按年龄、性别、族裔与收入进行人群分层",
                    "睡眠与活动行为负担摘要",
                    "机构级叙述性报告输出",
                ],
                "not_supported_yet": [
                    "抑郁结局预测",
                    "基于真实结果的公平性指标",
                    "贝叶斯决策阈值优化",
                ],
                "next_required_file": "P_DPQ.xpt（PHQ-9 抑郁筛查模块）",
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

        frame = self._filtered_frame(min_age=min_age, max_age=max_age)
        filtered_total_weight = float(frame["WTINTPRP"].dropna().sum())
        rows: list[dict[str, Any]] = []
        for group_value, subset in frame.groupby(group_by, dropna=False):
            if len(subset) < min_participants:
                continue
            weighted_share = None
            subset_weight = float(subset["WTINTPRP"].dropna().sum())
            if filtered_total_weight > 0:
                weighted_share = subset_weight / filtered_total_weight * 100
            elevated_rate = self._weighted_series_rate(
                subset, subset["screening_priority_score"] >= 3
            )
            rows.append(
                {
                    "group": "未知" if pd.isna(group_value) else str(group_value),
                    "participants": int(len(subset)),
                    "weighted_share_pct": self._round(weighted_share),
                    "avg_weekday_sleep_hours": self._round(
                        self._weighted_mean(subset, "weekday_sleep_hours")
                    ),
                    "avg_weekend_sleep_hours": self._round(
                        self._weighted_mean(subset, "weekend_sleep_hours")
                    ),
                    "avg_sedentary_hours_day": self._round(
                        self._weighted_mean(subset, "sedentary_hours_day")
                    ),
                    "short_sleep_rate_pct": self._round(
                        self._weighted_rate_pct(subset, "short_sleep_flag")
                    ),
                    "low_recreation_rate_pct": self._round(
                        self._weighted_rate_pct(subset, "low_recreation_flag")
                    ),
                    "elevated_priority_rate_pct": self._round(
                        elevated_rate * 100 if elevated_rate is not None else None
                    ),
                    "mean_priority_score": self._round(
                        self._weighted_mean(subset, "screening_priority_score")
                    ),
                }
            )

        rows.sort(key=lambda item: item["elevated_priority_rate_pct"] or 0, reverse=True)
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
        frame = self.analysis_frame.copy()
        grouped_rows: list[dict[str, Any]] = []
        for group_values, subset in frame.groupby(
            ["age_band", "gender", "income_band"], dropna=False
        ):
            age_band, gender, income_band = group_values
            metrics = self._priority_cohort_metrics(subset)
            grouped_rows.append(
                {
                    "age_band": str(age_band),
                    "gender": str(gender),
                    "income_band": str(income_band),
                    **metrics,
                }
            )
        grouped = pd.DataFrame(grouped_rows)
        grouped = grouped[grouped["participants"] >= min_participants]
        grouped = grouped.sort_values(
            by=["elevated_priority_rate_pct", "mean_priority_score", "participants"],
            ascending=[False, False, False],
        ).head(limit)

        rows: list[dict[str, Any]] = []
        for _, row in grouped.iterrows():
            rows.append(
                {
                    "age_band": row["age_band"],
                    "gender": row["gender"],
                    "income_band": row["income_band"],
                    "participants": int(row["participants"]),
                    "avg_weekday_sleep_hours": self._round(row["avg_weekday_sleep_hours"]),
                    "short_sleep_rate_pct": self._round(row["short_sleep_rate_pct"]),
                    "elevated_priority_rate_pct": self._round(
                        row["elevated_priority_rate_pct"]
                    ),
                    "mean_priority_score": self._round(row["mean_priority_score"]),
                }
            )
        return {
            "definition": "高优先级综合了短睡眠、周末睡眠差、久坐、休闲活动不足与低收入信号。",
            "rows": rows,
        }

    def _priority_cohort_metrics(self, subset: pd.DataFrame) -> dict[str, Any]:
        return {
            "participants": int(len(subset)),
            "avg_weekday_sleep_hours": self._weighted_mean(
                subset, "weekday_sleep_hours"
            ),
            "short_sleep_rate_pct": self._weighted_rate_pct(subset, "short_sleep_flag"),
            "elevated_priority_rate_pct": self._weighted_series_rate_pct(
                subset, subset["screening_priority_score"] >= 3
            ),
            "mean_priority_score": self._weighted_mean(
                subset, "screening_priority_score"
            ),
        }

    def audience_report(self, audience: str) -> dict[str, Any]:
        audience = audience.lower()
        supported = {"researcher", "manager", "clinical", "engineering"}
        if audience not in supported:
            raise ValueError(f"audience must be one of: {', '.join(sorted(supported))}")

        top_cohorts = self.priority_cohorts(limit=3, min_participants=100)["rows"]
        summary = self.summary()
        short_sleep = summary["behavioral_signals"]["short_sleep_rate_pct"]
        elevated = summary["behavioral_signals"]["elevated_rate_pct"]

        shared_notes = [
            "当前结果适用于群体洞察、筛查支持与机构汇报场景。",
            "平台输出的是机构级健康信息，不替代正式临床诊断。",
            "不同角色可基于同一份分析结果查看各自更关心的重点内容。",
        ]

        if audience == "researcher":
            headline = "面向研究团队的人群特征洞察与重点群体发现摘要。"
            focus = [
                f"当前加权短睡眠率约为 {short_sleep}%，可作为群体行为负担观察的基础指标。",
                f"约有 {elevated}% 的加权样本处于重点关注层级，适合进一步开展分层分析。",
                "低收入群体中的重点信号更集中，适合用于后续研究假设与重点样本讨论。",
            ]
        elif audience == "manager":
            headline = "面向管理团队的重点人群识别与资源配置支持摘要。"
            focus = [
                "优先查看哪些年龄与收入组合呈现出更高的重点关注比例。",
                "将简报结果用于筛查安排、服务排序与阶段性项目汇报更有价值。",
                "建议把平台作为运营支持与资源配置工具，而不是个体诊断工具。",
            ]
        elif audience == "clinical":
            headline = "面向临床团队的筛查支持与重点对象关注摘要。"
            focus = [
                "将睡眠与活动行为特征作为筛查流程中的背景性参考信号。",
                "更适合用于识别需要进一步关注的人群，而不是直接下诊断结论。",
                "可将结果与现有筛查流程结合，用于优化触达顺序与复核重点。",
            ]
        else:
            headline = "面向技术团队的接口接入与平台集成摘要。"
            focus = [
                "当前接口适合接入内部看板、展示页与汇报系统。",
                "统一的数据处理与特征衍生逻辑，有助于保证不同前端入口结果一致。",
                "后续可在此基础上继续扩展上传分析、任务调度与报告导出能力。",
            ]

        return {
            "audience": audience,
            "headline": headline,
            "focus_points": focus,
            "top_cohorts": top_cohorts,
            "shared_notes": shared_notes,
        }

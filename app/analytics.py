from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import StringIO
import math
import os
from pathlib import Path
import re
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
CHARLS_CESD_NEGATIVE_ITEMS = [
    "dc016",
    "dc017",
    "dc018",
    "dc019",
    "dc021",
    "dc022",
    "dc024",
    "dc025",
]
CHARLS_CESD_POSITIVE_ITEMS = ["dc020", "dc023"]
CHARLS_CESD_ITEMS = CHARLS_CESD_NEGATIVE_ITEMS + CHARLS_CESD_POSITIVE_ITEMS
CHARLS_NUMERIC_SENTINELS = [-1, -2, -7, -8, -9, 97, 98, 99, 997, 999]
CHARLS_PROFILE_FIELDS = {
    "age_band",
    "gender",
    "income_band",
    "education_band",
    "sleep_band",
    "chronic_band",
    "priority_tier",
    "mental_health_severity_band",
    "residence_band",
    "hukou_band",
}
CHARLS_COMPARISON_FIELDS = {
    "age_band",
    "gender",
    "income_band",
    "education_band",
    "sleep_band",
}
CUSTOM_GROUP_FIELDS = {
    "age_band",
    "gender",
    "race_ethnicity",
    "income_band",
    "education_band",
    "sleep_band",
    "bmi_band",
    "chronic_band",
    "priority_tier",
    "mental_health_severity_band",
    "residence_band",
}
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
CHARLS_GENDER_LABELS = {
    1.0: "男性",
    2.0: "女性",
}
CHARLS_EDUCATION_LABELS = {
    1.0: "未受正规教育",
    2.0: "未读完小学",
    3.0: "私塾 / 在家教育",
    4.0: "小学",
    5.0: "初中",
    6.0: "高中",
    7.0: "职业学校",
    8.0: "大专",
    9.0: "本科",
    10.0: "硕士",
    11.0: "博士",
}
CHARLS_RESIDENCE_LABELS = {
    1.0: "城镇中心",
    2.0: "城乡结合区",
    3.0: "农村",
    4.0: "特殊区域",
}
CHARLS_HUKOU_LABELS = {
    1.0: "农业户口",
    2.0: "非农业户口",
    3.0: "统一居民户口",
    4.0: "无户口",
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
CSV_IMPORT_ALIASES = {
    "age": ["age", "age_years", "ridageyr"],
    "gender": ["gender", "sex", "gender_label"],
    "sleep_hours": ["sleep_hours", "weekday_sleep_hours", "sleep", "sleep_duration"],
    "income_band": ["income_band", "income_level", "income"],
    "education_band": ["education_band", "education_level", "education"],
    "mental_health_score": [
        "mental_health_score",
        "score",
        "phq9_total",
        "phq_9_total",
        "cesd10_total",
        "ces_d10_total",
    ],
    "bmi": ["bmi", "body_mass_index"],
    "chronic_condition_count": [
        "chronic_condition_count",
        "chronic_count",
        "comorbidity_count",
    ],
    "weight": ["weight", "sample_weight"],
    "race_ethnicity": ["race_ethnicity", "race", "ethnicity"],
    "residence_band": ["residence_band", "residence", "residence_type"],
    "weekend_sleep_hours": ["weekend_sleep_hours", "weekend_sleep"],
}
CSV_TEMPLATE_COLUMNS = [
    "age",
    "gender",
    "sleep_hours",
    "income_band",
    "education_band",
    "bmi",
    "chronic_condition_count",
    "mental_health_score",
    "weight",
    "race_ethnicity",
    "residence_band",
]


@dataclass(frozen=True)
class DatasetInfo:
    filename: str
    label: str
    role: str
    source: str


class NHANESAnalyticsService:
    """Multi-branch analytics service.

    - NHANES/: current North America mental-health analytics built around PHQ-9.
    - data/: historical baseline used for behavior context.
    - CHARLS2020r/: China branch built around CES-D10 and CHARLS covariates.
    """

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.current_data_dir = project_dir / "NHANES"
        self.legacy_data_dir = project_dir / "data"
        self.charls_data_dir = project_dir / "CHARLS2020r"
        self.current_weight_column = "WTMEC2YR"
        self.legacy_weight_column = "WTMECPRP"
        self.charls_weight_column = "INDV_weight_ad2"
        self.custom_weight_column = "sample_weight"
        self.custom_dataset_frames: dict[str, pd.DataFrame] = {}
        self.custom_dataset_meta: dict[str, dict[str, Any]] = {}

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
        self.charls_datasets = [
            DatasetInfo(
                "Sample_Infor.dta",
                "样本信息",
                "筛选 2020 横截面样本并识别有效观察值",
                "charls",
            ),
            DatasetInfo(
                "Weights.dta",
                "抽样权重",
                "提供个人层面的 CHARLS 权重",
                "charls",
            ),
            DatasetInfo(
                "Demographic_Background.dta",
                "人口学背景",
                "年龄、性别、教育、户口与城乡背景",
                "charls",
            ),
            DatasetInfo(
                "Health_Status_and_Functioning.dta",
                "健康与功能",
                "CES-D10、睡眠时长与慢病信息",
                "charls",
            ),
            DatasetInfo(
                "Household_Income.dta",
                "家庭收支",
                "使用家庭月支出作为社会经济代理变量",
                "charls",
            ),
        ]

        self._ensure_current_files()
        self._ensure_legacy_files()
        self._ensure_charls_files()

        self.current_source_frames = {
            info.filename: self._load_xpt(self.current_data_dir / info.filename)
            for info in self.current_datasets
        }
        self.legacy_source_frames = {
            info.filename: self._load_xpt(self.legacy_data_dir / info.filename)
            for info in self.legacy_datasets
        }
        self.charls_source_frames = {
            info.filename: self._load_dta(self.charls_data_dir / info.filename)
            for info in self.charls_datasets
        }

        self.analysis_frame = self._prepare_current_analysis_frame()
        self.phq_ready_frame = self.analysis_frame[
            self.analysis_frame["mental_health_total"].notna()
        ].copy()
        self.legacy_frame = self._prepare_legacy_analysis_frame()
        self.charls_frame = self._prepare_charls_analysis_frame()
        self.charls_ready_frame = self.charls_frame[
            self.charls_frame["mental_health_total"].notna()
        ].copy()

        self.current_total_weight = float(
            self.analysis_frame[self.current_weight_column].dropna().sum()
        )
        self.current_phq_ready_weight = float(
            self.phq_ready_frame[self.current_weight_column].dropna().sum()
        )
        self.legacy_total_weight = float(
            self.legacy_frame[self.legacy_weight_column].dropna().sum()
        )
        self.charls_total_weight = float(
            self.charls_frame[self.charls_weight_column].dropna().sum()
        )
        self.charls_ready_weight = float(
            self.charls_ready_frame[self.charls_weight_column].dropna().sum()
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
        missing = [
            dataset.filename
            for dataset in self.legacy_datasets
            if not (self.legacy_data_dir / dataset.filename).exists()
        ]
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(
                f"缺少历史基线文件：{joined}。请确认这些文件位于 data 目录。"
            )

    def _ensure_charls_files(self) -> None:
        missing = [
            dataset.filename
            for dataset in self.charls_datasets
            if not (self.charls_data_dir / dataset.filename).exists()
        ]
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(
                f"缺少 CHARLS 文件：{joined}。请确认这些文件位于 CHARLS2020r 目录。"
            )

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

    def _load_dta(self, path: Path) -> pd.DataFrame:
        frame = pd.read_stata(path, convert_categoricals=False)
        return self._clean_frame(frame)

    def _clean_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        cleaned = frame.copy()
        numeric_sentinels = list(dict.fromkeys(NUMERIC_SENTINELS + CHARLS_NUMERIC_SENTINELS))
        for column in cleaned.columns:
            series = cleaned[column]
            if pd.api.types.is_numeric_dtype(series):
                numeric_series = series.astype(float)
                numeric_series = numeric_series.mask(numeric_series.abs() < 1e-70, 0.0)
                cleaned[column] = numeric_series.replace(numeric_sentinels, np.nan)
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
        frame["mental_health_total"] = frame["PHQ9_total"]
        frame["mental_health_high_risk"] = frame["PHQ9_high_risk"]
        frame["mental_health_severity_band"] = frame["phq_severity_band"]
        frame["mental_health_scale"] = "PHQ-9"
        frame["mental_health_threshold_default"] = 10.0
        frame["analysis_eligible"] = frame["PHQ9_total"].notna()

    def _prepare_charls_analysis_frame(self) -> pd.DataFrame:
        sample = self.charls_source_frames["Sample_Infor.dta"][
            ["ID", "householdID", "communityID", "crosssection", "died", "iyear", "imonth"]
        ].copy()
        weights = self.charls_source_frames["Weights.dta"][
            ["ID", "householdID", "communityID", "INDV_weight", "INDV_weight_ad2"]
        ].copy()
        demographics = self.charls_source_frames["Demographic_Background.dta"][
            ["ID", "householdID", "communityID", "xrage", "zrgender", "zredu", "ba008", "ba009"]
        ].copy()
        health = self.charls_source_frames["Health_Status_and_Functioning.dta"][
            [
                "ID",
                "householdID",
                "communityID",
                "da030",
                *CHARLS_CESD_ITEMS,
                *[f"zdisease_{index}_" for index in range(1, 16)],
            ]
        ].copy()
        household_income = self.charls_source_frames["Household_Income.dta"][
            ["householdID", "communityID", "gf001"]
        ].copy()

        cross_section = sample[sample["crosssection"].fillna(0) == 1].copy()
        merged = (
            cross_section.merge(weights, on=["ID", "householdID", "communityID"], how="left")
            .merge(demographics, on=["ID", "householdID", "communityID"], how="left")
            .merge(health, on=["ID", "householdID", "communityID"], how="left")
            .merge(household_income, on=["householdID", "communityID"], how="left")
        )

        self._apply_charls_demographic_bands(merged)
        self._apply_charls_sleep_bands(merged)
        self._apply_charls_specific_features(merged)
        return merged

    def _apply_charls_demographic_bands(self, frame: pd.DataFrame) -> None:
        frame["RIDAGEYR"] = frame["xrage"]
        frame["gender"] = frame["zrgender"].map(CHARLS_GENDER_LABELS).fillna("未知")
        frame["race_ethnicity"] = "中国样本"
        frame["education_band"] = frame["zredu"].map(CHARLS_EDUCATION_LABELS).fillna("缺失")
        frame["age_band"] = pd.cut(
            frame["xrage"],
            bins=[17, 44, 54, 64, 74, np.inf],
            labels=["18-44", "45-54", "55-64", "65-74", "75+"],
        )
        frame["age_band"] = frame["age_band"].astype("object").fillna("未知")
        frame["residence_band"] = frame["ba008"].map(CHARLS_RESIDENCE_LABELS).fillna("缺失")
        frame["hukou_band"] = frame["ba009"].map(CHARLS_HUKOU_LABELS).fillna("缺失")

        expenditure = frame["gf001"]
        valid_expenditure = expenditure.dropna()
        if valid_expenditure.empty:
            frame["income_band"] = "缺失"
        else:
            q1 = float(valid_expenditure.quantile(1 / 3))
            q2 = float(valid_expenditure.quantile(2 / 3))
            if q1 == q2:
                q2 = q1 + 1e-9
            frame["income_band"] = pd.cut(
                expenditure,
                bins=[-np.inf, q1, q2, np.inf],
                labels=["较低支出", "中等支出", "较高支出"],
            )
            frame["income_band"] = frame["income_band"].astype("object").fillna("缺失")

    def _apply_charls_sleep_bands(self, frame: pd.DataFrame) -> None:
        frame["weekday_sleep_hours"] = frame["da030"]
        frame["weekend_sleep_hours"] = np.nan
        frame["sleep_gap_hours"] = np.nan
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

    def _apply_charls_specific_features(self, frame: pd.DataFrame) -> None:
        chronic_columns = [f"zdisease_{index}_" for index in range(1, 16)]
        frame["chronic_condition_count"] = frame[chronic_columns].notna().sum(axis=1).astype(float)
        frame["chronic_band"] = pd.cut(
            frame["chronic_condition_count"],
            bins=[-1, 0, 1, np.inf],
            labels=["无慢病", "1项慢病", "2项及以上"],
        )
        frame["chronic_band"] = frame["chronic_band"].astype("object").fillna("缺失")

        for column in CHARLS_CESD_NEGATIVE_ITEMS + CHARLS_CESD_POSITIVE_ITEMS:
            frame[column] = frame[column].replace({997: np.nan, 999: np.nan})
        for column in CHARLS_CESD_NEGATIVE_ITEMS:
            frame[f"{column}_score"] = frame[column] - 1
        for column in CHARLS_CESD_POSITIVE_ITEMS:
            frame[f"{column}_score"] = 4 - frame[column]

        cesd_score_columns = [f"{column}_score" for column in CHARLS_CESD_ITEMS]
        frame["CESD10_total"] = frame[cesd_score_columns].sum(axis=1, min_count=len(CHARLS_CESD_ITEMS))
        frame["CESD10_high_risk"] = np.where(
            frame["CESD10_total"].notna(),
            frame["CESD10_total"] >= 10,
            np.nan,
        )
        frame["mental_health_severity_band"] = pd.cut(
            frame["CESD10_total"],
            bins=[-np.inf, 9, 19, np.inf],
            labels=["低风险(0-9)", "中风险(10-19)", "高风险(20-30)"],
        )
        frame["mental_health_severity_band"] = (
            frame["mental_health_severity_band"].astype("object").fillna("缺失")
        )

        frame["low_income_flag"] = np.where(
            frame["income_band"].notna(),
            frame["income_band"].eq("较低支出"),
            np.nan,
        )
        frame["BMXBMI"] = np.nan
        frame["bmi_band"] = "缺失"
        frame["obesity_flag"] = np.nan
        frame["multi_chronic_flag"] = np.where(
            frame["chronic_condition_count"].notna(),
            frame["chronic_condition_count"] >= 2,
            np.nan,
        )

        priority_components = pd.DataFrame(
            {
                "cesd_high_risk": frame["CESD10_high_risk"],
                "short_sleep": frame["short_sleep_flag"],
                "low_expenditure": frame["low_income_flag"],
                "multi_chronic": frame["multi_chronic_flag"],
            },
            index=frame.index,
        )
        frame["support_priority_score"] = (
            priority_components.fillna(False).astype(int).sum(axis=1)
        )
        frame["priority_tier"] = frame["support_priority_score"].map(PRIORITY_TIER_LABELS)
        frame["mental_health_total"] = frame["CESD10_total"]
        frame["mental_health_high_risk"] = frame["CESD10_high_risk"]
        frame["mental_health_scale"] = "CES-D10"
        frame["mental_health_threshold_default"] = 10.0
        frame["analysis_eligible"] = frame["mental_health_total"].notna()

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

    def _filtered_charls_frame(
        self,
        min_age: int = 18,
        max_age: int = 80,
        require_mental_health: bool = False,
    ) -> pd.DataFrame:
        frame = self.charls_ready_frame if require_mental_health else self.charls_frame
        return frame[
            (frame["xrage"].fillna(-1) >= min_age)
            & (frame["xrage"].fillna(999) <= max_age)
        ].copy()

    @staticmethod
    def _slugify_custom_label(label: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
        return normalized or "custom-dataset"

    @staticmethod
    def _custom_dataset_token(dataset_key: str) -> str:
        return f"custom:{dataset_key}"

    @staticmethod
    def _default_series(frame: pd.DataFrame, value: Any = np.nan) -> pd.Series:
        return pd.Series([value] * len(frame), index=frame.index)

    @staticmethod
    def _normalize_gender_label(value: Any) -> str:
        text = str(value).strip().lower()
        mapping = {
            "1": "男性",
            "m": "男性",
            "male": "男性",
            "man": "男性",
            "男": "男性",
            "2": "女性",
            "f": "女性",
            "female": "女性",
            "woman": "女性",
            "女": "女性",
        }
        return mapping.get(text, str(value).strip() if str(value).strip() else "未知")

    @staticmethod
    def _normalize_income_band_label(value: Any) -> str:
        text = str(value).strip().lower()
        mapping = {
            "low": "低收入",
            "较低": "低收入",
            "较低收入": "低收入",
            "低收入": "低收入",
            "mid": "中等收入",
            "medium": "中等收入",
            "middle": "中等收入",
            "中等": "中等收入",
            "中等收入": "中等收入",
            "high": "较高收入",
            "较高": "较高收入",
            "较高收入": "较高收入",
            "高收入": "较高收入",
            "low spend": "较低支出",
            "较低支出": "较低支出",
            "mid spend": "中等支出",
            "中等支出": "中等支出",
            "high spend": "较高支出",
            "较高支出": "较高支出",
        }
        return mapping.get(text, str(value).strip() if str(value).strip() else "缺失")

    @staticmethod
    def _normalize_residence_label(value: Any) -> str:
        text = str(value).strip().lower()
        mapping = {
            "urban": "城市",
            "city": "城市",
            "城市": "城市",
            "suburban": "城乡结合",
            "城乡结合": "城乡结合",
            "rural": "农村",
            "village": "农村",
            "农村": "农村",
        }
        return mapping.get(text, str(value).strip() if str(value).strip() else "未指定")

    def _ensure_unique_custom_key(self, label: str) -> str:
        base_key = self._slugify_custom_label(label)
        candidate = base_key
        suffix = 2
        while candidate in self.custom_dataset_meta:
            candidate = f"{base_key}-{suffix}"
            suffix += 1
        return candidate

    def _custom_dataset_entry(self, dataset_key: str) -> dict[str, Any]:
        token = self._custom_dataset_token(dataset_key)
        if dataset_key not in self.custom_dataset_meta or dataset_key not in self.custom_dataset_frames:
            raise ValueError(f"custom dataset not found: {token}")
        return {
            "key": dataset_key,
            "token": token,
            "meta": self.custom_dataset_meta[dataset_key],
            "frame": self.custom_dataset_frames[dataset_key],
        }

    @staticmethod
    def _normalize_csv_columns(columns: list[str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for column in columns:
            key = re.sub(r"[^a-z0-9]+", "_", str(column).strip().lower()).strip("_")
            if key and key not in normalized:
                normalized[key] = str(column)
        return normalized

    def _find_csv_column(
        self,
        normalized_columns: dict[str, str],
        canonical_field: str,
        *,
        required: bool,
    ) -> str | None:
        aliases = CSV_IMPORT_ALIASES.get(canonical_field, [canonical_field])
        for alias in aliases:
            key = re.sub(r"[^a-z0-9]+", "_", alias.strip().lower()).strip("_")
            if key in normalized_columns:
                return normalized_columns[key]
        if required:
            raise ValueError(
                f"CSV missing required column '{canonical_field}'. "
                f"Accepted aliases: {', '.join(aliases)}"
            )
        return None

    def custom_dataset_csv_template(self) -> str:
        sample_rows = [
            [
                "45",
                "female",
                "5.5",
                "low",
                "high school",
                "28.4",
                "2",
                "13",
                "1.0",
                "Han",
                "urban",
            ],
            [
                "31",
                "male",
                "7.1",
                "middle",
                "college",
                "23.2",
                "0",
                "6",
                "1.2",
                "Han",
                "suburban",
            ],
        ]
        lines = [",".join(CSV_TEMPLATE_COLUMNS)]
        lines.extend(",".join(row) for row in sample_rows)
        return "\n".join(lines) + "\n"

    def _prepare_custom_analysis_frame(
        self,
        rows: list[dict[str, Any]],
        *,
        scale: str,
    ) -> pd.DataFrame:
        frame = pd.DataFrame(rows).copy()
        if frame.empty:
            raise ValueError("custom dataset rows cannot be empty")

        age_series = pd.to_numeric(
            frame.get("age", self._default_series(frame)),
            errors="coerce",
        )
        sleep_series = pd.to_numeric(
            frame.get("sleep_hours", self._default_series(frame)),
            errors="coerce",
        )
        bmi_series = pd.to_numeric(
            frame.get("bmi", self._default_series(frame)),
            errors="coerce",
        )
        chronic_series = pd.to_numeric(
            frame.get("chronic_condition_count", self._default_series(frame, 0)),
            errors="coerce",
        )
        score_series = pd.to_numeric(
            frame.get("mental_health_score", self._default_series(frame)),
            errors="coerce",
        )
        weight_series = pd.to_numeric(
            frame.get("weight", self._default_series(frame, 1.0)),
            errors="coerce",
        ).fillna(1.0)
        weight_series = weight_series.clip(lower=0.1)

        frame["RIDAGEYR"] = age_series
        frame["weekday_sleep_hours"] = sleep_series
        frame["weekend_sleep_hours"] = pd.to_numeric(
            frame.get("weekend_sleep_hours", sleep_series),
            errors="coerce",
        )
        frame["sleep_gap_hours"] = frame["weekend_sleep_hours"] - frame["weekday_sleep_hours"]
        frame["BMXBMI"] = bmi_series
        frame["chronic_condition_count"] = chronic_series.fillna(0)
        frame["mental_health_total"] = score_series
        frame[self.custom_weight_column] = weight_series
        frame["gender"] = frame.get(
            "gender",
            self._default_series(frame, "未知"),
        ).map(self._normalize_gender_label)
        frame["race_ethnicity"] = frame.get(
            "race_ethnicity",
            self._default_series(frame, "自定义样本"),
        ).fillna("自定义样本")
        frame["education_band"] = frame.get(
            "education_band",
            self._default_series(frame, "缺失"),
        ).fillna("缺失")
        frame["income_band"] = frame.get(
            "income_band",
            self._default_series(frame, "缺失"),
        ).map(self._normalize_income_band_label)
        frame["residence_band"] = frame.get(
            "residence_band",
            self._default_series(frame, "未指定"),
        ).map(self._normalize_residence_label)
        frame["hukou_band"] = "未指定"

        frame["age_band"] = pd.cut(
            frame["RIDAGEYR"],
            bins=[17, 24, 34, 49, 64, np.inf],
            labels=["18-24", "25-34", "35-49", "50-64", "65+"],
        )
        frame["age_band"] = frame["age_band"].astype("object").fillna("未知")
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
        frame["bmi_band"] = pd.cut(
            frame["BMXBMI"],
            bins=[-np.inf, 18.5, 25, 30, np.inf],
            labels=["偏瘦", "正常", "超重", "肥胖"],
        )
        frame["bmi_band"] = frame["bmi_band"].astype("object").fillna("缺失")
        frame["chronic_band"] = pd.cut(
            frame["chronic_condition_count"],
            bins=[-1, 0, 1, np.inf],
            labels=["无慢病", "1项慢病", "2项及以上"],
        )
        frame["chronic_band"] = frame["chronic_band"].astype("object").fillna("缺失")
        frame["low_income_flag"] = np.where(
            frame["income_band"].notna(),
            frame["income_band"].isin({"低收入", "较低支出"}),
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

        normalized_scale = str(scale).strip().upper()
        if normalized_scale == "CES-D10":
            threshold_default = 10
            threshold_max = 30
            frame["mental_health_high_risk"] = np.where(
                frame["mental_health_total"].notna(),
                frame["mental_health_total"] >= threshold_default,
                np.nan,
            )
            frame["mental_health_severity_band"] = pd.cut(
                frame["mental_health_total"],
                bins=[-np.inf, 9, 19, np.inf],
                labels=["低风险(0-9)", "中风险(10-19)", "高风险(20-30)"],
            )
            frame["CESD10_total"] = frame["mental_health_total"]
        else:
            normalized_scale = "PHQ-9"
            threshold_default = 10
            threshold_max = 27
            frame["mental_health_high_risk"] = np.where(
                frame["mental_health_total"].notna(),
                frame["mental_health_total"] >= threshold_default,
                np.nan,
            )
            frame["mental_health_severity_band"] = pd.cut(
                frame["mental_health_total"],
                bins=[-np.inf, 4, 9, 14, 19, 27],
                labels=[
                    "最轻(0-4)",
                    "轻度(5-9)",
                    "中度(10-14)",
                    "中重度(15-19)",
                    "重度(20-27)",
                ],
            )
            frame["PHQ9_total"] = frame["mental_health_total"]
        frame["mental_health_severity_band"] = (
            frame["mental_health_severity_band"].astype("object").fillna("缺失")
        )

        priority_components = pd.DataFrame(
            {
                "mental_high_risk": frame["mental_health_high_risk"],
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
        frame["mental_health_scale"] = normalized_scale
        frame["mental_health_threshold_default"] = float(threshold_default)
        frame["analysis_eligible"] = frame["mental_health_total"].notna()
        return frame

    def register_custom_dataset(
        self,
        label: str,
        rows: list[dict[str, Any]],
        *,
        scale: str = "PHQ-9",
        source_kind: str = "manual",
    ) -> dict[str, Any]:
        clean_label = label.strip() or "自定义样本"
        dataset_key = self._ensure_unique_custom_key(clean_label)
        frame = self._prepare_custom_analysis_frame(rows, scale=scale)
        ready = frame[frame["mental_health_total"].notna()].copy()
        threshold_default = int(frame["mental_health_threshold_default"].dropna().iloc[0])
        threshold_max = 27 if str(frame["mental_health_scale"].dropna().iloc[0]) == "PHQ-9" else 30
        self.custom_dataset_frames[dataset_key] = frame
        self.custom_dataset_meta[dataset_key] = {
            "label": clean_label,
            "source_kind": source_kind,
            "scale": str(frame["mental_health_scale"].dropna().iloc[0]),
            "threshold_default": threshold_default,
            "threshold_max": threshold_max,
            "adult_rows": int(len(frame)),
            "mental_health_complete_rows": int(len(ready)),
            "weighted_population_estimate": self._round(float(frame[self.custom_weight_column].sum()), 0),
        }
        return self.custom_dataset_descriptor(dataset_key)

    def import_csv_dataset(
        self,
        label: str,
        csv_content: str,
        *,
        scale: str = "PHQ-9",
    ) -> dict[str, Any]:
        if not csv_content or not csv_content.strip():
            raise ValueError("csv_content cannot be empty")

        try:
            source = pd.read_csv(StringIO(csv_content.strip()))
        except Exception as exc:  # pragma: no cover - pandas raises several parser errors
            raise ValueError(f"Unable to parse CSV content: {exc}") from exc

        if source.empty:
            raise ValueError("CSV contains no rows")

        source.columns = [str(column).replace("\ufeff", "").strip() for column in source.columns]

        normalized_columns = self._normalize_csv_columns(source.columns.tolist())
        required_fields = [
            "age",
            "gender",
            "sleep_hours",
            "income_band",
            "education_band",
            "mental_health_score",
        ]
        optional_fields = [
            "bmi",
            "chronic_condition_count",
            "weight",
            "race_ethnicity",
            "residence_band",
            "weekend_sleep_hours",
        ]

        column_mapping: dict[str, str] = {}
        selected_columns: dict[str, str] = {}
        for field in required_fields:
            selected_column = self._find_csv_column(normalized_columns, field, required=True)
            if selected_column is not None:
                selected_columns[field] = selected_column
                column_mapping[field] = selected_column
        for field in optional_fields:
            selected_column = self._find_csv_column(normalized_columns, field, required=False)
            if selected_column is not None:
                selected_columns[field] = selected_column
                column_mapping[field] = selected_column

        renamed = source.rename(columns={source_name: field for field, source_name in selected_columns.items()})
        allowed_fields = set(required_fields) | set(optional_fields)
        records = renamed[[field for field in renamed.columns if field in allowed_fields]].to_dict("records")
        dataset = self.register_custom_dataset(
            label=label,
            rows=records,
            scale=scale,
            source_kind="uploaded_csv",
        )
        return {
            "dataset": dataset,
            "import_summary": {
                "source_rows": int(len(source)),
                "accepted_rows": dataset["adult_rows"],
                "required_fields": required_fields,
                "optional_fields": optional_fields,
                "column_mapping": column_mapping,
            },
        }

    def generate_demo_dataset(
        self,
        label: str,
        sample_size: int = 240,
        *,
        profile: str = "balanced",
        scale: str = "PHQ-9",
        seed: int | None = None,
    ) -> dict[str, Any]:
        if sample_size < 30 or sample_size > 5000:
            raise ValueError("sample_size must be between 30 and 5000")

        normalized_profile = profile.strip().lower()
        supported_profiles = {"balanced", "sleep_stress", "older_chronic", "community_outreach"}
        if normalized_profile not in supported_profiles:
            raise ValueError(
                "profile must be one of: balanced, sleep_stress, older_chronic, community_outreach"
            )

        rng = np.random.default_rng(seed)
        scale_name = "CES-D10" if str(scale).strip().upper() == "CES-D10" else "PHQ-9"
        score_max = 30 if scale_name == "CES-D10" else 27
        score_base = 7 if scale_name == "CES-D10" else 5
        rows: list[dict[str, Any]] = []

        for _ in range(sample_size):
            if normalized_profile == "sleep_stress":
                age = int(np.clip(rng.normal(36, 11), 18, 80))
                sleep_hours = float(np.clip(rng.normal(5.5, 1.2), 3.5, 10))
                income_band = rng.choice(["低收入", "中等收入", "较高收入"], p=[0.45, 0.4, 0.15])
                chronic_count = int(np.clip(rng.poisson(1.1), 0, 6))
            elif normalized_profile == "older_chronic":
                age = int(np.clip(rng.normal(61, 9), 35, 85))
                sleep_hours = float(np.clip(rng.normal(6.3, 1.1), 4, 10))
                income_band = rng.choice(["低收入", "中等收入", "较高收入"], p=[0.35, 0.45, 0.2])
                chronic_count = int(np.clip(rng.poisson(2.2), 0, 7))
            elif normalized_profile == "community_outreach":
                age = int(np.clip(rng.normal(48, 15), 18, 85))
                sleep_hours = float(np.clip(rng.normal(6.0, 1.4), 3.5, 10))
                income_band = rng.choice(["低收入", "中等收入", "较高收入"], p=[0.5, 0.35, 0.15])
                chronic_count = int(np.clip(rng.poisson(1.5), 0, 7))
            else:
                age = int(np.clip(rng.normal(43, 14), 18, 82))
                sleep_hours = float(np.clip(rng.normal(6.8, 1.2), 4, 10))
                income_band = rng.choice(["低收入", "中等收入", "较高收入"], p=[0.3, 0.45, 0.25])
                chronic_count = int(np.clip(rng.poisson(0.9), 0, 5))

            gender = rng.choice(["男性", "女性"], p=[0.46, 0.54])
            education_band = rng.choice(
                ["低于9年级", "9-11年级", "高中 / GED", "部分大学 / 副学士", "大学及以上"],
                p=[0.12, 0.16, 0.28, 0.24, 0.2],
            )
            race_ethnicity = rng.choice(
                ["非西班牙裔白人", "非西班牙裔黑人", "墨西哥裔美国人", "非西班牙裔亚裔", "其他 / 多族裔"],
                p=[0.36, 0.18, 0.18, 0.16, 0.12],
            )
            residence_band = rng.choice(["城市", "城乡结合", "农村"], p=[0.42, 0.24, 0.34])
            bmi = float(np.clip(rng.normal(26.4, 4.7), 16, 43))
            risk_score = score_base + rng.normal(0, 2.4)
            if sleep_hours < 6:
                risk_score += 4.0
            if income_band == "低收入":
                risk_score += 2.4
            if chronic_count >= 2:
                risk_score += 3.0
            if bmi >= 30:
                risk_score += 1.2
            if age >= 65:
                risk_score += 0.8
            if gender == "女性":
                risk_score += 0.6
            if normalized_profile == "sleep_stress":
                risk_score += 1.8
            elif normalized_profile == "older_chronic":
                risk_score += 1.2
            elif normalized_profile == "community_outreach":
                risk_score += 1.5

            rows.append(
                {
                    "age": age,
                    "gender": gender,
                    "sleep_hours": round(sleep_hours, 1),
                    "income_band": income_band,
                    "education_band": education_band,
                    "bmi": round(bmi, 1),
                    "chronic_condition_count": chronic_count,
                    "mental_health_score": round(float(np.clip(risk_score, 0, score_max)), 1),
                    "weight": round(float(rng.uniform(0.8, 1.8)), 2),
                    "race_ethnicity": race_ethnicity,
                    "residence_band": residence_band,
                }
            )

        return self.register_custom_dataset(
            label=label,
            rows=rows,
            scale=scale_name,
            source_kind=f"synthetic:{normalized_profile}",
        )

    def custom_dataset_descriptor(self, dataset_key: str) -> dict[str, Any]:
        entry = self._custom_dataset_entry(dataset_key)
        meta = entry["meta"]
        return {
            "id": entry["token"],
            "key": dataset_key,
            "label": meta["label"],
            "scale": meta["scale"],
            "source_kind": meta["source_kind"],
            "adult_rows": meta["adult_rows"],
            "mental_health_complete_rows": meta["mental_health_complete_rows"],
            "weighted_population_estimate": meta["weighted_population_estimate"],
        }

    def list_custom_datasets(self) -> dict[str, Any]:
        dataset_keys = sorted(
            self.custom_dataset_meta,
            key=lambda key: self.custom_dataset_meta[key]["label"].lower(),
        )
        return {
            "count": len(dataset_keys),
            "datasets": [self.custom_dataset_descriptor(key) for key in dataset_keys],
        }

    def _validate_dataset(self, dataset: str) -> str:
        normalized = dataset.lower().strip()
        if normalized.startswith("custom:"):
            dataset_key = normalized.split(":", 1)[1].strip()
            if not dataset_key:
                raise ValueError("custom dataset id cannot be empty")
            if dataset_key not in self.custom_dataset_meta:
                raise ValueError(
                    "custom dataset not found. Create one first via /api/v1/custom-datasets/generate or /manual"
                )
            return self._custom_dataset_token(dataset_key)
        aliases = {
            "current": "current",
            "nhanes": "current",
            "north_america": "current",
            "legacy": "legacy",
            "baseline": "legacy",
            "charls": "charls",
            "china": "charls",
            "asia": "charls",
        }
        if normalized not in aliases:
            raise ValueError("dataset must be one of: current, legacy, charls, custom:{id}")
        return aliases[normalized]

    def _mental_dataset_config(self, dataset: str) -> dict[str, Any]:
        selected = self._validate_dataset(dataset)
        if selected == "legacy":
            raise ValueError("legacy baseline does not support mental-health branch analytics")
        if selected.startswith("custom:"):
            dataset_key = selected.split(":", 1)[1]
            entry = self._custom_dataset_entry(dataset_key)
            frame = entry["frame"]
            meta = entry["meta"]
            return {
                "dataset": selected,
                "label": meta["label"],
                "region": "Custom",
                "country": "User provided",
                "analysis_frame": frame,
                "ready_frame": frame[frame["mental_health_total"].notna()].copy(),
                "weight_column": self.custom_weight_column,
                "group_fields": CUSTOM_GROUP_FIELDS,
                "comparison_fields": SHARED_GROUP_FIELDS,
                "score_column": "mental_health_total",
                "high_risk_column": "mental_health_high_risk",
                "severity_column": "mental_health_severity_band",
                "sleep_hours_column": "weekday_sleep_hours",
                "bmi_column": "BMXBMI",
                "threshold_default": meta["threshold_default"],
                "threshold_max": meta["threshold_max"],
                "source_kind": meta["source_kind"],
            }
        if selected == "current":
            return {
                "dataset": "current",
                "label": "NHANES August 2021-August 2023",
                "region": "North America",
                "country": "United States",
                "analysis_frame": self.analysis_frame,
                "ready_frame": self.phq_ready_frame,
                "weight_column": self.current_weight_column,
                "group_fields": CURRENT_GROUP_FIELDS,
                "comparison_fields": SHARED_GROUP_FIELDS,
                "score_column": "mental_health_total",
                "high_risk_column": "mental_health_high_risk",
                "severity_column": "mental_health_severity_band",
                "sleep_hours_column": "weekday_sleep_hours",
                "bmi_column": "BMXBMI",
                "threshold_default": 10,
                "threshold_max": 27,
            }
        return {
            "dataset": "charls",
            "label": "CHARLS 2020 Wave 5",
            "region": "Asia",
            "country": "China",
            "analysis_frame": self.charls_frame,
            "ready_frame": self.charls_ready_frame,
            "weight_column": self.charls_weight_column,
            "group_fields": CHARLS_PROFILE_FIELDS,
            "comparison_fields": CHARLS_COMPARISON_FIELDS,
            "score_column": "mental_health_total",
            "high_risk_column": "mental_health_high_risk",
            "severity_column": "mental_health_severity_band",
            "sleep_hours_column": "weekday_sleep_hours",
            "bmi_column": "BMXBMI",
            "threshold_default": 10,
            "threshold_max": 30,
        }

    def _filtered_mental_frame(
        self,
        dataset: str,
        min_age: int = 18,
        max_age: int = 80,
        require_mental_health: bool = False,
    ) -> pd.DataFrame:
        selected = self._validate_dataset(dataset)
        if selected.startswith("custom:"):
            frame = self._custom_dataset_entry(selected.split(":", 1)[1])["frame"]
            if require_mental_health:
                frame = frame[frame["mental_health_total"].notna()].copy()
            return frame[
                (frame["RIDAGEYR"].fillna(-1) >= min_age)
                & (frame["RIDAGEYR"].fillna(999) <= max_age)
            ].copy()
        if selected == "current":
            return self._filtered_current_frame(
                min_age=min_age,
                max_age=max_age,
                require_phq=require_mental_health,
            )
        if selected == "charls":
            return self._filtered_charls_frame(
                min_age=min_age,
                max_age=max_age,
                require_mental_health=require_mental_health,
            )
        raise ValueError("legacy baseline does not support mental-health branch analytics")

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

    def _overall_high_risk_rate(
        self,
        dataset: str = "current",
        frame: pd.DataFrame | None = None,
    ) -> float | None:
        config = self._mental_dataset_config(dataset)
        target = config["ready_frame"] if frame is None else frame
        return self._weighted_rate_pct(
            target,
            config["high_risk_column"],
            config["weight_column"],
        )

    def _group_snapshot(
        self,
        frame: pd.DataFrame,
        group_by: str,
        weight_column: str,
        include_mental_health: bool,
        min_participants: int,
        score_column: str = "mental_health_total",
        high_risk_column: str = "mental_health_high_risk",
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
            if include_mental_health:
                eligible_subset = subset[subset[score_column].notna()].copy()
                snapshot.update(
                    {
                        "eligible_participants": int(len(eligible_subset)),
                        "mean_mental_health_score": self._round(
                            self._weighted_mean(
                                eligible_subset,
                                score_column,
                                weight_column,
                            )
                        ),
                        "mean_phq9_score": self._round(
                            self._weighted_mean(
                                eligible_subset,
                                score_column,
                                weight_column,
                            )
                        ),
                        "high_risk_rate_pct": self._round(
                            self._weighted_rate_pct(
                                eligible_subset,
                                high_risk_column,
                                weight_column,
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
            "service_mode": "multi-branch",
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
            "charls_cycle": {
                "label": "CHARLS 2020 Wave 5",
                "join_key": "ID / householdID / communityID",
                "target_label": "CESD10_high_risk",
                "files": build_files(self.charls_datasets, self.charls_source_frames),
                "adult_rows": int(len(self.charls_frame)),
                "mental_health_ready_rows": int(len(self.charls_ready_frame)),
            },
            "custom_datasets": self.list_custom_datasets(),
        }

    def capabilities(self) -> dict[str, Any]:
        available_datasets = [
            {
                "id": "current",
                "label": "NHANES current branch",
                "region": "North America",
                "scale": "PHQ-9",
            },
            {
                "id": "charls",
                "label": "CHARLS China branch",
                "region": "Asia",
                "scale": "CES-D10",
            },
            {
                "id": "legacy",
                "label": "Legacy behavior baseline",
                "region": "North America",
                "scale": None,
            },
        ]
        available_datasets.extend(
            {
                "id": descriptor["id"],
                "label": descriptor["label"],
                "region": "Custom",
                "scale": descriptor["scale"],
            }
            for descriptor in self.list_custom_datasets()["datasets"]
        )
        return {
            "service": "HealthInsight API",
            "version": "2.1.0",
            "style": {
                "base_path": "/api/v1",
                "docs": "/docs",
                "openapi": "/api/v1/openapi.json",
            },
            "available_datasets": available_datasets,
            "current_modules": [
                "PHQ-9 风险识别",
                "CHARLS 中国分支",
                "假数据生成与手工录入工作台",
                "多分支人群画像",
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
                    "current 分支基于 NHANES 与 PHQ-9，charls 分支基于 CHARLS 与 CES-D10。",
                    "legacy 分支仅作为历史行为背景对照，不直接提供心理量表高风险输出。",
                ],
            },
        }

    def summary(self, dataset: str = "current") -> dict[str, Any]:
        selected = self._validate_dataset(dataset)
        if selected == "legacy":
            legacy_short_sleep = self._weighted_rate_pct(
                self.legacy_frame,
                "short_sleep_flag",
                self.legacy_weight_column,
            )
            return {
                "service_mode": "multi-branch",
                "selected_dataset": "legacy",
                "selected_branch": {
                    "label": "Legacy behavior baseline",
                    "region": "North America",
                    "adult_rows": int(len(self.legacy_frame)),
                    "weighted_population_estimate": self._round(self.legacy_total_weight, 0),
                },
                "baseline_behavior_signals": {
                    "legacy_short_sleep_rate_pct": self._round(legacy_short_sleep),
                    "legacy_any_activity_rate_pct": self._round(
                        self._weighted_rate_pct(
                            self.legacy_frame,
                            "any_activity_flag",
                            self.legacy_weight_column,
                        )
                    ),
                    "legacy_inactive_rate_pct": self._round(
                        self._weighted_rate_pct(
                            self.legacy_frame,
                            "inactive_flag",
                            self.legacy_weight_column,
                        )
                    ),
                },
            }

        config = self._mental_dataset_config(selected)
        frame = config["analysis_frame"]
        ready = config["ready_frame"]
        weight_column = config["weight_column"]
        score_column = config["score_column"]
        high_risk_column = config["high_risk_column"]

        high_risk_rate = self._weighted_rate_pct(ready, high_risk_column, weight_column)
        current_short_sleep = self._weighted_rate_pct(frame, "short_sleep_flag", weight_column)
        baseline_reference = self.threshold_simulation(
            threshold=config["threshold_default"],
            weekly_capacity=20,
            dataset=selected,
        )

        if selected == "current":
            sample = {
                "demographics_rows": int(len(self.current_source_frames["DEMO_L.xpt"])),
                "phq_rows": int(len(self.current_source_frames["DPQ_L.xpt"])),
                "sleep_rows": int(len(self.current_source_frames["SLQ_L.xpt"])),
                "body_measure_rows": int(len(self.current_source_frames["BMX_L.xpt"])),
                "medical_condition_rows": int(len(self.current_source_frames["MCQ_L.xpt"])),
                "merged_adult_rows": int(len(frame)),
                "mental_health_complete_rows": int(len(ready)),
            }
            coverage = {
                "phq_complete_pct": self._round(frame["PHQ9_total"].notna().mean() * 100),
                "weekday_sleep_hours_pct": self._round(frame["weekday_sleep_hours"].notna().mean() * 100),
                "bmi_pct": self._round(frame["BMXBMI"].notna().mean() * 100),
                "income_ratio_pct": self._round(frame["INDFMPIR"].notna().mean() * 100),
                "chronic_question_pct": self._round(frame["MCQ160A"].notna().mean() * 100),
            }
        elif selected == "charls":
            sample = {
                "sample_info_rows": int(len(self.charls_source_frames["Sample_Infor.dta"])),
                "weights_rows": int(len(self.charls_source_frames["Weights.dta"])),
                "demographics_rows": int(len(self.charls_source_frames["Demographic_Background.dta"])),
                "health_rows": int(len(self.charls_source_frames["Health_Status_and_Functioning.dta"])),
                "household_income_rows": int(len(self.charls_source_frames["Household_Income.dta"])),
                "merged_adult_rows": int(len(frame)),
                "mental_health_complete_rows": int(len(ready)),
            }
            coverage = {
                "phq_complete_pct": self._round(frame["CESD10_total"].notna().mean() * 100),
                "weekday_sleep_hours_pct": self._round(frame["weekday_sleep_hours"].notna().mean() * 100),
                "bmi_pct": self._round(frame["BMXBMI"].notna().mean() * 100),
                "income_ratio_pct": self._round(frame["gf001"].notna().mean() * 100),
                "chronic_question_pct": self._round(frame["zdisease_1_"].notna().mean() * 100),
            }
        else:
            sample = {
                "source_kind": config.get("source_kind"),
                "custom_rows": int(len(frame)),
                "mental_health_complete_rows": int(len(ready)),
            }
            coverage = {
                "phq_complete_pct": self._round(frame["mental_health_total"].notna().mean() * 100),
                "weekday_sleep_hours_pct": self._round(frame["weekday_sleep_hours"].notna().mean() * 100),
                "bmi_pct": self._round(frame["BMXBMI"].notna().mean() * 100),
                "income_ratio_pct": self._round(frame["income_band"].notna().mean() * 100),
                "chronic_question_pct": self._round(frame["chronic_condition_count"].notna().mean() * 100),
            }

        mental_mean_score = self._weighted_mean(ready, score_column, weight_column)
        mental_signals = {
            "scale": str(ready["mental_health_scale"].dropna().iloc[0]) if not ready.empty else None,
            "mean_score": self._round(mental_mean_score),
            "mean_phq9_score": self._round(mental_mean_score),
            "high_risk_rate_pct": self._round(high_risk_rate),
            "phq_high_risk_rate_pct": self._round(high_risk_rate),
            "severe_rate_pct": self._round(
                self._weighted_series_rate_pct(
                    ready,
                    ready[score_column] >= 20,
                    weight_column,
                )
            ),
        }

        response: dict[str, Any] = {
            "service_mode": "multi-branch",
            "selected_dataset": selected,
            "selected_branch": {
                "label": config["label"],
                "region": config["region"],
                "country": config["country"],
                "adult_rows": int(len(frame)),
                "mental_health_complete_rows": int(len(ready)),
                "weighted_population_estimate": self._round(
                    float(frame[weight_column].dropna().sum()),
                    0,
                ),
            },
            "sample": sample,
            "coverage": coverage,
            "mental_health_signals": mental_signals,
            "shared_signals": {
                "current_short_sleep_rate_pct": self._round(current_short_sleep),
                "current_avg_sleep_hours": self._round(
                    self._weighted_mean(frame, "weekday_sleep_hours", weight_column)
                ),
            },
            "threshold_reference": baseline_reference,
            "current_boundary": {
                "supported": [
                    "可选数据分支的机构级心理健康洞察",
                    "分层画像与重点队列识别",
                    "阈值模拟与初步资源估算",
                    "面向管理、研究与临床团队的简报输出",
                ],
                "not_supported_yet": [
                    "个体临床诊断",
                    "不同量表原始分数的直接横向比较",
                    "基于独立预测模型的公平性审计",
                ],
            },
        }

        if selected == "current":
            legacy_short_sleep = self._weighted_rate_pct(
                self.legacy_frame,
                "short_sleep_flag",
                self.legacy_weight_column,
            )
            response["legacy_cycle"] = {
                "label": "Legacy behavior baseline",
                "adult_rows": int(len(self.legacy_frame)),
                "weighted_population_estimate": self._round(self.legacy_total_weight, 0),
            }
            response["baseline_behavior_signals"] = {
                "legacy_short_sleep_rate_pct": self._round(legacy_short_sleep),
                "legacy_any_activity_rate_pct": self._round(
                    self._weighted_rate_pct(
                        self.legacy_frame,
                        "any_activity_flag",
                        self.legacy_weight_column,
                    )
                ),
                "legacy_inactive_rate_pct": self._round(
                    self._weighted_rate_pct(
                        self.legacy_frame,
                        "inactive_flag",
                        self.legacy_weight_column,
                    )
                ),
            }
            response["shared_signals"].update(
                {
                    "legacy_short_sleep_rate_pct": self._round(legacy_short_sleep),
                    "short_sleep_gap_pct_point": self._round(
                        None
                        if current_short_sleep is None or legacy_short_sleep is None
                        else current_short_sleep - legacy_short_sleep
                    ),
                    "legacy_avg_sleep_hours": self._round(
                        self._weighted_mean(
                            self.legacy_frame,
                            "weekday_sleep_hours",
                            self.legacy_weight_column,
                        )
                    ),
                }
            )
        else:
            reference_short_sleep = self._weighted_rate_pct(
                self.analysis_frame,
                "short_sleep_flag",
                self.current_weight_column,
            )
            response["reference_branch"] = {
                "dataset": "current",
                "label": "NHANES August 2021-August 2023",
                "region": "North America",
            }
            response["shared_signals"].update(
                {
                    "legacy_short_sleep_rate_pct": self._round(reference_short_sleep),
                    "short_sleep_gap_pct_point": self._round(
                        None
                        if current_short_sleep is None or reference_short_sleep is None
                        else current_short_sleep - reference_short_sleep
                    ),
                    "legacy_avg_sleep_hours": self._round(
                        self._weighted_mean(
                            self.analysis_frame,
                            "weekday_sleep_hours",
                            self.current_weight_column,
                        )
                    ),
                }
            )
            if selected.startswith("custom:"):
                response["selected_branch"]["source_kind"] = config.get("source_kind")
                response["selected_branch"]["country"] = "Custom sample"

        return response

    def population_profile(
        self,
        group_by: str,
        dataset: str = "current",
        min_age: int = 18,
        max_age: int = 80,
        min_participants: int = 50,
    ) -> dict[str, Any]:
        config = self._mental_dataset_config(dataset)
        if group_by not in config["group_fields"]:
            raise ValueError(
                f"group_by must be one of: {', '.join(sorted(config['group_fields']))}"
            )

        frame = self._filtered_mental_frame(
            dataset=dataset,
            min_age=min_age,
            max_age=max_age,
            require_mental_health=False,
        )
        weight_column = config["weight_column"]
        score_column = config["score_column"]
        high_risk_column = config["high_risk_column"]
        filtered_total_weight = float(frame[weight_column].dropna().sum())
        rows: list[dict[str, Any]] = []

        for group_value, subset in frame.groupby(group_by, dropna=False):
            if len(subset) < min_participants:
                continue

            ready_subset = subset[subset[score_column].notna()].copy()
            subset_weight = float(subset[weight_column].dropna().sum())
            weighted_share = (
                subset_weight / filtered_total_weight * 100
                if filtered_total_weight > 0
                else None
            )
            high_risk_rate = self._weighted_rate_pct(
                ready_subset,
                high_risk_column,
                weight_column,
            )
            mean_score = self._weighted_mean(ready_subset, score_column, weight_column)

            rows.append(
                {
                    "group": "未知" if pd.isna(group_value) else str(group_value),
                    "participants": int(len(subset)),
                    "eligible_participants": int(len(ready_subset)),
                    "weighted_share_pct": self._round(weighted_share),
                    "phq_complete_pct": self._round(
                        ready_subset.shape[0] / subset.shape[0] * 100 if len(subset) else None
                    ),
                    "mean_mental_health_score": self._round(mean_score),
                    "mean_phq9_score": self._round(mean_score),
                    "high_risk_rate_pct": self._round(high_risk_rate),
                    "avg_weekday_sleep_hours": self._round(
                        self._weighted_mean(subset, "weekday_sleep_hours", weight_column)
                    ),
                    "avg_bmi": self._round(
                        self._weighted_mean(subset, "BMXBMI", weight_column)
                    ),
                    "mean_chronic_condition_count": self._round(
                        self._weighted_mean(subset, "chronic_condition_count", weight_column)
                    ),
                    "short_sleep_rate_pct": self._round(
                        self._weighted_rate_pct(subset, "short_sleep_flag", weight_column)
                    ),
                    "multi_chronic_rate_pct": self._round(
                        self._weighted_rate_pct(subset, "multi_chronic_flag", weight_column)
                    ),
                }
            )

        rows.sort(key=lambda item: item["high_risk_rate_pct"] or 0, reverse=True)
        return {
            "dataset": config["dataset"],
            "group_by": group_by,
            "filters": {
                "min_age": min_age,
                "max_age": max_age,
                "min_participants": min_participants,
            },
            "rows": rows,
        }

    def priority_cohorts(
        self,
        limit: int = 8,
        min_participants: int = 80,
        dataset: str = "current",
    ) -> dict[str, Any]:
        config = self._mental_dataset_config(dataset)
        frame = self._filtered_mental_frame(dataset=dataset, require_mental_health=True)
        weight_column = config["weight_column"]
        score_column = config["score_column"]
        high_risk_column = config["high_risk_column"]
        overall_rate = self._overall_high_risk_rate(dataset=dataset, frame=frame) or 0.0

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
                high_risk_column,
                weight_column,
            )
            mean_score = self._weighted_mean(subset, score_column, weight_column)
            grouped_rows.append(
                {
                    "age_band": str(age_band),
                    "income_band": str(income_band),
                    "sleep_band": str(sleep_band),
                    "segment_label": f"{age_band} / {income_band} / {sleep_band}",
                    "participants": int(len(subset)),
                    "mean_mental_health_score": self._round(mean_score),
                    "mean_phq9_score": self._round(mean_score),
                    "high_risk_rate_pct": self._round(high_risk_rate),
                    "short_sleep_rate_pct": self._round(
                        self._weighted_rate_pct(subset, "short_sleep_flag", weight_column)
                    ),
                    "multi_chronic_rate_pct": self._round(
                        self._weighted_rate_pct(subset, "multi_chronic_flag", weight_column)
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
            "dataset": config["dataset"],
            "definition": (
                "重点组合以当前分支的心理健康高风险比例为核心，同时参考睡眠、收入与慢病负担。"
            ),
            "rows": rows,
        }

    def risk_patterns(
        self,
        limit: int = 6,
        min_participants: int = 60,
        dataset: str = "current",
    ) -> dict[str, Any]:
        rows = self.priority_cohorts(
            limit=limit,
            min_participants=min_participants,
            dataset=dataset,
        )["rows"]
        return {
            "dataset": self._mental_dataset_config(dataset)["dataset"],
            "definition": "风险模式用于快速发现同时承受年龄、收入与睡眠压力的人群组合。",
            "rows": rows,
        }

    def risk_factors(
        self,
        limit: int = 8,
        min_participants: int = 120,
        dataset: str = "current",
    ) -> dict[str, Any]:
        config = self._mental_dataset_config(dataset)
        frame = self._filtered_mental_frame(dataset=dataset, require_mental_health=True)
        weight_column = config["weight_column"]
        score_column = config["score_column"]
        high_risk_column = config["high_risk_column"]
        overall_rate = self._overall_high_risk_rate(dataset=dataset, frame=frame) or 0.0
        rows: list[dict[str, Any]] = []
        dimensions = [
            ("收入层", "income_band"),
            ("睡眠层", "sleep_band"),
            ("教育层", "education_band"),
            ("慢病负担", "chronic_band"),
            ("年龄层", "age_band"),
            ("性别", "gender"),
        ]
        if config["dataset"] == "current":
            dimensions.insert(2, ("BMI 分层", "bmi_band"))
            dimensions.append(("族裔", "race_ethnicity"))
        elif config["dataset"] == "charls":
            dimensions.extend([("城乡层", "residence_band"), ("户口层", "hukou_band")])
        else:
            dimensions.insert(2, ("BMI 分层", "bmi_band"))
            dimensions.extend([("族裔", "race_ethnicity"), ("居住地", "residence_band")])

        for dimension_label, field in dimensions:
            for group_value, subset in frame.groupby(field, dropna=False):
                if len(subset) < min_participants:
                    continue
                group_name = "未知" if pd.isna(group_value) else str(group_value)
                if group_name in {"未知", "缺失"}:
                    continue
                high_risk_rate = self._weighted_rate_pct(
                    subset,
                    high_risk_column,
                    weight_column,
                )
                if high_risk_rate is None:
                    continue
                mean_score = self._weighted_mean(subset, score_column, weight_column)
                rows.append(
                    {
                        "dimension": dimension_label,
                        "group": group_name,
                        "participants": int(len(subset)),
                        "mean_mental_health_score": self._round(mean_score),
                        "mean_phq9_score": self._round(mean_score),
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
            "dataset": config["dataset"],
            "overall_high_risk_rate_pct": self._round(overall_rate),
            "rows": rows[:limit],
        }

    def cycle_comparison(
        self,
        group_by: str = "age_band",
        dataset: str = "current",
        min_age: int = 18,
        max_age: int = 80,
        min_participants: int = 80,
    ) -> dict[str, Any]:
        selected = self._validate_dataset(dataset)
        if selected == "current":
            allowed_fields = SHARED_GROUP_FIELDS
            if group_by not in allowed_fields:
                raise ValueError(f"group_by must be one of: {', '.join(sorted(allowed_fields))}")
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
                include_mental_health=True,
                min_participants=min_participants,
                score_column="mental_health_total",
                high_risk_column="mental_health_high_risk",
            )
            legacy_rows = self._group_snapshot(
                legacy_frame,
                group_by,
                self.legacy_weight_column,
                include_mental_health=False,
                min_participants=min_participants,
            )
            selected_label = "NHANES August 2021-August 2023"
            baseline_label = "Legacy behavior baseline"
            selected_scale = "PHQ-9"
            baseline_has_mental_health = False
        elif selected == "charls":
            allowed_fields = CHARLS_COMPARISON_FIELDS
            if group_by not in allowed_fields:
                raise ValueError(f"group_by must be one of: {', '.join(sorted(allowed_fields))}")
            current_frame = self._filtered_charls_frame(
                min_age=min_age,
                max_age=max_age,
                require_mental_health=True,
            )
            legacy_frame = self._filtered_current_frame(
                min_age=min_age,
                max_age=max_age,
                require_phq=True,
            )
            current_rows = self._group_snapshot(
                current_frame,
                group_by,
                self.charls_weight_column,
                include_mental_health=True,
                min_participants=min_participants,
                score_column="mental_health_total",
                high_risk_column="mental_health_high_risk",
            )
            legacy_rows = self._group_snapshot(
                legacy_frame,
                group_by,
                self.current_weight_column,
                include_mental_health=True,
                min_participants=min_participants,
                score_column="mental_health_total",
                high_risk_column="mental_health_high_risk",
            )
            selected_label = "CHARLS 2020 Wave 5"
            baseline_label = "NHANES August 2021-August 2023"
            selected_scale = "CES-D10"
            baseline_has_mental_health = True
        else:
            allowed_fields = SHARED_GROUP_FIELDS
            if group_by not in allowed_fields:
                raise ValueError(f"group_by must be one of: {', '.join(sorted(allowed_fields))}")
            current_frame = self._filtered_mental_frame(
                dataset=selected,
                min_age=min_age,
                max_age=max_age,
                require_mental_health=True,
            )
            legacy_frame = self._filtered_current_frame(
                min_age=min_age,
                max_age=max_age,
                require_phq=True,
            )
            config = self._mental_dataset_config(selected)
            current_rows = self._group_snapshot(
                current_frame,
                group_by,
                self.custom_weight_column,
                include_mental_health=True,
                min_participants=min_participants,
                score_column="mental_health_total",
                high_risk_column="mental_health_high_risk",
            )
            legacy_rows = self._group_snapshot(
                legacy_frame,
                group_by,
                self.current_weight_column,
                include_mental_health=True,
                min_participants=min_participants,
                score_column="mental_health_total",
                high_risk_column="mental_health_high_risk",
            )
            selected_label = config["label"]
            baseline_label = "NHANES August 2021-August 2023"
            selected_scale = str(current_frame["mental_health_scale"].dropna().iloc[0]) if not current_frame.empty else None
            baseline_has_mental_health = True

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
                    "current_mean_mental_health_score": current.get("mean_mental_health_score"),
                    "current_short_sleep_rate_pct": current_short_sleep,
                    "baseline_short_sleep_rate_pct": legacy_short_sleep,
                    "baseline_high_risk_rate_pct": legacy.get("high_risk_rate_pct"),
                    "baseline_mean_mental_health_score": legacy.get("mean_mental_health_score"),
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
            "dataset": selected,
            "group_by": group_by,
            "selected_branch_label": selected_label,
            "baseline_branch_label": baseline_label,
            "selected_scale": selected_scale,
            "baseline_has_mental_health": baseline_has_mental_health,
            "filters": {
                "min_age": min_age,
                "max_age": max_age,
                "min_participants": min_participants,
            },
            "definition": (
                "current 分支默认对照 legacy 行为基线；charls 与 custom 分支默认对照当前 NHANES 分支。"
            ),
            "rows": merged_rows,
        }

    def threshold_simulation(
        self,
        threshold: int = 10,
        weekly_capacity: int = 20,
        dataset: str = "current",
    ) -> dict[str, Any]:
        config = self._mental_dataset_config(dataset)
        if threshold < 0 or threshold > config["threshold_max"]:
            raise ValueError(f"threshold must be between 0 and {config['threshold_max']}")
        if weekly_capacity < 1 or weekly_capacity > 10000:
            raise ValueError("weekly_capacity must be between 1 and 10000")

        frame = self._filtered_mental_frame(dataset=dataset, require_mental_health=True)
        score_column = config["score_column"]
        weight_column = config["weight_column"]
        default_threshold = config["threshold_default"]
        flagged = frame[score_column] >= threshold
        baseline = frame[score_column] >= default_threshold

        weighted_flagged_pct = self._weighted_series_rate_pct(
            frame,
            flagged,
            weight_column,
        )
        weighted_baseline_pct = self._weighted_series_rate_pct(
            frame,
            baseline,
            weight_column,
        )
        flagged_n = int(flagged.sum())
        baseline_n = int(baseline.sum())
        mean_flagged_score = self._weighted_mean(
            frame[flagged],
            score_column,
            weight_column,
        )
        counselor_weeks = math.ceil(flagged_n / weekly_capacity) if flagged_n else 0

        if threshold <= max(default_threshold - 2, 1):
            recommendation = "更敏感的设置，适合优先减少漏筛。"
        elif threshold <= default_threshold + 2:
            recommendation = "更平衡的设置，适合常规筛查与初步转介。"
        else:
            recommendation = "更保守的设置，适合资源有限的场景。"

        return {
            "dataset": config["dataset"],
            "scale": str(frame["mental_health_scale"].dropna().iloc[0]) if not frame.empty else None,
            "threshold": threshold,
            "default_threshold": default_threshold,
            "weekly_capacity": weekly_capacity,
            "flagged_n": flagged_n,
            "flagged_weighted_pct": self._round(weighted_flagged_pct),
            "mean_flagged_mental_health_score": self._round(mean_flagged_score),
            "mean_flagged_phq9_score": self._round(mean_flagged_score),
            "delta_vs_threshold_10_pct_point": self._round(
                None
                if weighted_flagged_pct is None or weighted_baseline_pct is None
                else weighted_flagged_pct - weighted_baseline_pct
            ),
            "delta_vs_default_threshold_n": flagged_n - baseline_n,
            "delta_vs_threshold_10_n": flagged_n - baseline_n,
            "estimated_counselor_weeks": counselor_weeks,
            "recommended_use": recommendation,
        }

    def audience_report(self, audience: str, dataset: str = "current") -> dict[str, Any]:
        audience = audience.lower()
        supported = {"researcher", "manager", "clinical", "engineering"}
        if audience not in supported:
            raise ValueError(f"audience must be one of: {', '.join(sorted(supported))}")

        config = self._mental_dataset_config(dataset)
        is_custom = str(config["dataset"]).startswith("custom:")
        cohort_min_participants = 3 if is_custom else 80
        risk_factor_min_participants = 3 if is_custom else 120
        top_cohorts = self.priority_cohorts(
            limit=3,
            min_participants=cohort_min_participants,
            dataset=dataset,
        )["rows"]
        summary = self.summary(dataset=dataset)
        risk_factors = self.risk_factors(
            limit=3,
            min_participants=risk_factor_min_participants,
            dataset=dataset,
        )["rows"]
        high_risk = summary["mental_health_signals"]["phq_high_risk_rate_pct"]
        mean_phq = summary["mental_health_signals"]["mean_phq9_score"]
        current_short_sleep = summary["shared_signals"]["current_short_sleep_rate_pct"]
        comparison_short_sleep = summary["shared_signals"].get("legacy_short_sleep_rate_pct")

        shared_notes = [
            f"基于 {config['label']} · {summary['mental_health_signals']['scale']} 量表",
            "平台输出群体风险分析，不替代临床诊断。",
        ]

        if audience == "researcher":
            headline = f"{config['label']} 心理健康风险研究摘要"
            focus = [
                f"高风险比例 {high_risk}%，平均分 {mean_phq}。",
                f"短睡眠率 {current_short_sleep}%（参考分支 {comparison_short_sleep}%），可用于背景对照。",
                "建议围绕收入、睡眠和慢病负担做分层分析。",
            ]
        elif audience == "manager":
            headline = f"{config['label']} 高风险人群优先筛查建议"
            focus = [
                f"高风险占比 {high_risk}%，平均分 {mean_phq}。",
                "低收入、短睡眠、慢病负担高的人群风险最突出。",
                "建议优先向重点人群投入筛查与外展资源。",
            ]
        elif audience == "clinical":
            headline = f"{config['label']} 优先复核人群建议"
            focus = [
                f"阈值 10 以上筛出 {high_risk}% 人群，建议优先复核。",
                "短睡眠、经济压力、慢病负担可作为访谈背景线索。",
                "量表结果仅作为筛查起点，不构成诊断结论。",
            ]
        else:
            headline = "技术架构与接口概览"
            focus = [
                f"current={config['label']} · PHQ-9；charls=CHARLS · CES-D10。",
                "接口结构统一，支持前端展示、报告导出与后续模型接入。",
                "可在现有框架上扩展公平性检查、批量导出与异步任务。",
            ]

        return {
            "audience": audience,
            "dataset": config["dataset"],
            "headline": headline,
            "focus_points": focus,
            "top_cohorts": top_cohorts,
            "top_risk_factors": risk_factors,
            "shared_notes": shared_notes,
        }

    def institution_report(
        self,
        dataset: str = "current",
        *,
        audience: str = "manager",
        organization_name: str = "示例机构",
        report_title: str | None = None,
        threshold: int | None = None,
        weekly_capacity: int = 20,
    ) -> dict[str, Any]:
        audience_name = audience.lower().strip() or "manager"
        if audience_name not in {"researcher", "manager", "clinical", "engineering"}:
            raise ValueError("audience must be one of: researcher, manager, clinical, engineering")

        config = self._mental_dataset_config(dataset)
        selected_dataset = config["dataset"]
        summary = self.summary(dataset=selected_dataset)
        audience_snapshot = self.audience_report(audience_name, dataset=selected_dataset)
        audience_display_map = {
            "researcher": "研究团队",
            "manager": "管理团队",
            "clinical": "临床团队",
            "engineering": "技术团队",
        }
        audience_display = audience_display_map[audience_name]
        is_custom = str(selected_dataset).startswith("custom:")
        min_participants = 3 if is_custom else 80
        risk_factor_min_participants = 3 if is_custom else 120
        threshold_value = threshold if threshold is not None else config["threshold_default"]
        top_cohorts = self.priority_cohorts(
            limit=5,
            min_participants=min_participants,
            dataset=selected_dataset,
        )["rows"]
        risk_factors = self.risk_factors(
            limit=5,
            min_participants=risk_factor_min_participants,
            dataset=selected_dataset,
        )["rows"]
        threshold_plan = self.threshold_simulation(
            threshold=threshold_value,
            weekly_capacity=weekly_capacity,
            dataset=selected_dataset,
        )
        comparison = self.cycle_comparison(
            dataset=selected_dataset,
            group_by="age_band",
            min_participants=min_participants,
        )

        branch = summary["selected_branch"]
        signals = summary["mental_health_signals"]
        shared = summary["shared_signals"]
        adult_rows = int(branch["adult_rows"])
        complete_rows = int(summary["sample"]["mental_health_complete_rows"])
        completion_pct = self._round(
            complete_rows / adult_rows * 100 if adult_rows else None
        )
        high_risk_rate = signals["high_risk_rate_pct"] or 0
        mean_score = signals["mean_score"]
        short_sleep_rate = shared["current_short_sleep_rate_pct"]
        short_sleep_gap = shared.get("short_sleep_gap_pct_point")

        if high_risk_rate >= 25:
            risk_label = "高风险"
        elif high_risk_rate >= 15:
            risk_label = "较高风险"
        elif high_risk_rate >= 8:
            risk_label = "中等风险"
        else:
            risk_label = "常规监测"

        coverage_labels = {
            "phq_complete_pct": "量表完整度",
            "weekday_sleep_hours_pct": "睡眠字段完整度",
            "bmi_pct": "BMI 字段完整度",
            "income_ratio_pct": "收入字段完整度",
            "chronic_question_pct": "慢病字段完整度",
        }
        quality_checks: list[dict[str, Any]] = []
        for key, label in coverage_labels.items():
            value = summary["coverage"].get(key)
            if value is None:
                status = "unknown"
            elif value >= 90:
                status = "good"
            elif value >= 70:
                status = "watch"
            else:
                status = "needs_attention"
            quality_checks.append({"label": label, "value_pct": value, "status": status})

        comparison_highlights = [
            row
            for row in comparison["rows"]
            if row.get("current_high_risk_rate_pct") is not None
        ][:3]
        lead_cohort = top_cohorts[0] if top_cohorts else None
        lead_factor = risk_factors[0] if risk_factors else None
        lead_comparison = comparison_highlights[0] if comparison_highlights else None
        lead_cohort_label = (
            str(lead_cohort["segment_label"])
            if lead_cohort and lead_cohort.get("segment_label")
            else "当前重点高风险组合"
        )
        lead_factor_label = (
            f"{lead_factor['dimension']} / {lead_factor['group']}"
            if lead_factor
            else "重点风险分层"
        )
        lead_comparison_label = (
            str(lead_comparison["group"])
            if lead_comparison and lead_comparison.get("group")
            else "主要年龄分层"
        )

        base_summary = [
            f"{organization_name} 共纳入 {adult_rows} 人，{complete_rows} 人具备完整量表（完整率 {completion_pct}%）。",
            f"高风险占比 {high_risk_rate}%，平均分 {mean_score}，综合判断：「{risk_label}」。",
        ]

        if audience_name == "researcher":
            executive_summary = base_summary + [
                f"建议围绕 {lead_factor_label} 做分层解释，结合 {lead_comparison_label} 对照结果检验结论稳定性。",
            ]
            priority_actions = [
                {
                    "title": "固化分析口径",
                    "owner": "研究团队",
                    "timeline": "1 周内",
                    "detail": f"记录 {signals['scale']} 阈值、样本范围和字段覆盖率，确保复现口径一致。",
                },
                {
                    "title": "分层敏感性分析",
                    "owner": "研究团队",
                    "timeline": "2 周内",
                    "detail": f"围绕 {lead_factor_label} 与 {lead_cohort_label} 做分层，确认结论稳定性。",
                },
                {
                    "title": "整理汇报素材",
                    "owner": "课题组",
                    "timeline": "本轮后",
                    "detail": "将关键发现和样本完整度整理成图表，便于写入论文或项目汇报。",
                },
            ]
            audience_notes = ["研究视角关注样本覆盖与分层稳定性。"]
        elif audience_name == "clinical":
            executive_summary = base_summary + [
                f"阈值 {threshold_plan['threshold']} 命中 {threshold_plan['flagged_n']} 人，建议优先联系 {lead_cohort_label}。",
            ]
            priority_actions = [
                {
                    "title": "生成首轮复核名单",
                    "owner": "心理服务团队",
                    "timeline": "1 周内",
                    "detail": f"按阈值 {threshold_plan['threshold']} 整理访谈对象，优先覆盖 {lead_cohort_label}。",
                },
                {
                    "title": "制定转介节奏",
                    "owner": "临床督导",
                    "timeline": "2 周内",
                    "detail": f"每周承接 {weekly_capacity} 人，约需 {threshold_plan['estimated_counselor_weeks']} 周完成首轮。",
                },
                {
                    "title": "补充沟通背景",
                    "owner": "临床团队",
                    "timeline": "复核同步",
                    "detail": "以睡眠、经济压力和慢病负担作为访谈线索，提升效率。",
                },
            ]
            audience_notes = ["量表高风险结果仅作为复核起点，不构成诊断结论。"]
        elif audience_name == "engineering":
            executive_summary = base_summary + [
                f"{config['label']} 分支已组织为结构化 JSON + Markdown，适合封装为导出、监控与批量任务。",
            ]
            priority_actions = [
                {
                    "title": "固化接口契约",
                    "owner": "后端 / 前端",
                    "timeline": "1 周内",
                    "detail": "固定 /api/v1/institution-report 字段语义与多分支参数，避免兼容性问题。",
                },
                {
                    "title": "增加字段监控",
                    "owner": "数据工程",
                    "timeline": "2 周内",
                    "detail": f"监控量表完整度 {completion_pct}% 及低覆盖字段，提前暴露数据缺口。",
                },
                {
                    "title": "批量导出任务化",
                    "owner": "平台工程",
                    "timeline": "联调后",
                    "detail": "将报告生成流程封装为定时任务，支持按周期自动刷新。",
                },
            ]
            audience_notes = ["技术视角关注接口稳定性与跨分支扩展能力。"]
        else:
            executive_summary = base_summary + [
                f"阈值 {threshold_plan['threshold']} 识别 {threshold_plan['flagged_n']} 人，每周承接 {weekly_capacity} 人，约需 {threshold_plan['estimated_counselor_weeks']} 周完成。",
            ]
            priority_actions = [
                {
                    "title": "生成首批筛查名单",
                    "owner": "项目负责人",
                    "timeline": "1 周内",
                    "detail": f"按阈值 {threshold_plan['threshold']} 导出高风险人群，首批 {threshold_plan['flagged_n']} 人。",
                },
                {
                    "title": "配置外展资源",
                    "owner": "运营团队",
                    "timeline": "2 周内",
                    "detail": f"优先面向 {lead_cohort_label} 安排宣教、外展和转介资源。",
                },
                {
                    "title": "补齐数据质量",
                    "owner": "数据治理",
                    "timeline": "本轮后",
                    "detail": f"当前量表完整率 {completion_pct}%，低于 70% 的字段优先补录。",
                },
            ]
            audience_notes = ["管理视角适合用于例会汇报、资源分配与筛查优先级讨论。"]

        key_findings: list[dict[str, Any]] = []
        if top_cohorts:
            first_cohort = top_cohorts[0]
            key_findings.append(
                {
                    "title": "重点人群已明确",
                    "detail": (
                        f"{first_cohort['segment_label']} 高风险占比 {first_cohort['high_risk_rate_pct']}%，"
                        f"高于总体 {first_cohort['uplift_vs_overall_pct_point']} 个百分点。"
                    ),
                }
            )
        if risk_factors:
            first_factor = risk_factors[0]
            key_findings.append(
                {
                    "title": "主要风险驱动可解释",
                    "detail": (
                        f"{first_factor['dimension']} / {first_factor['group']} 高风险率 "
                        f"{first_factor['high_risk_rate_pct']}%，较总体高 {first_factor['uplift_vs_overall_pct_point']} 个百分点。"
                    ),
                }
            )
        if short_sleep_rate is not None:
            gap_text = f"，较参考变化 {short_sleep_gap}pt" if short_sleep_gap is not None else ""
            key_findings.append(
                {
                    "title": "短睡眠信号",
                    "detail": f"短睡眠占比 {short_sleep_rate}%{gap_text}，建议纳入服务优先级。",
                }
            )
        if audience_name == "researcher" and comparison_highlights:
            key_findings.append(
                {
                    "title": "分层对照可深挖",
                    "detail": (
                        f"{lead_comparison_label} 在当前与参考分支间存在可追踪差异，"
                        "适合作为机制分析与敏感性检验的切入点。"
                    ),
                }
            )
        elif audience_name == "clinical":
            key_findings.append(
                {
                    "title": "复核顺序可落地",
                    "detail": (
                        f"按当前阈值，可先从 {lead_cohort_label} 启动复核，"
                        "使首轮名单与承接能力匹配。"
                    ),
                }
            )
        elif audience_name == "engineering":
            key_findings.append(
                {
                    "title": "链路已具备接口化基础",
                    "detail": (
                        f"已覆盖 {config['label']} 分支、结构化 JSON 和 Markdown 报告，"
                        "便于接入导出或异步任务系统。"
                    ),
                }
            )

        notes = [
            f"基于 {config['label']} · {signals['scale']} 量表",
            "本报告用于群体风险识别与筛查规划，不替代临床诊断。",
            "跨量表比较应关注比例和结构变化，而非原始分数绝对值。",
        ]
        notes.extend(audience_notes)

        final_title = report_title or f"{organization_name} 心理健康风险识别报告"
        markdown_lines = [
            f"# {final_title}",
            "",
            f"**机构：** {organization_name}　|　**受众：** {audience_display}　|　**数据集：** {config['label']}",
            f"**风险等级：** {risk_label}　|　**高风险占比：** {high_risk_rate}%　|　**平均分：** {mean_score}　|　**量表：** {signals['scale']}",
            "",
            f"> {audience_snapshot['headline']}",
            "",
            "## 执行摘要",
        ]
        markdown_lines.extend([f"- {line}" for line in executive_summary])
        markdown_lines.extend(["", "## 关键发现"])
        if key_findings:
            for item in key_findings:
                markdown_lines.append(f"- **{item['title']}**　{item['detail']}")
        else:
            markdown_lines.append("- 暂无足够样本生成关键发现。")
        markdown_lines.extend(["", "## 优先行动"])
        for item in priority_actions:
                markdown_lines.append(f"- **{item['title']}**　{item['owner']}　{item['timeline']}：{item['detail']}")
        markdown_lines.extend(["", "## 数据质量"])
        markdown_lines.extend(
            [f"- {item['label']}: {item['value_pct']}%（{item['status']}）" for item in quality_checks]
        )
        markdown_lines.extend(["", "## 使用边界"])
        markdown_lines.extend([f"- {note}" for note in notes])
        markdown_lines.extend([
            "",
            f"---",
            f"生成时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}　|　HealthInsight",
        ])

        return {
            "report_type": "institution_risk_report",
            "report_title": final_title,
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "organization_name": organization_name,
            "audience": audience_name,
            "audience_display": audience_display,
            "audience_headline": audience_snapshot["headline"],
            "audience_focus_points": audience_snapshot["focus_points"],
            "dataset": selected_dataset,
            "dataset_label": config["label"],
            "score_scale": signals["scale"],
            "risk_level": {
                "label": risk_label,
                "high_risk_rate_pct": high_risk_rate,
                "mean_score": mean_score,
            },
            "executive_summary": executive_summary,
            "data_quality": {
                "adult_rows": adult_rows,
                "mental_health_complete_rows": complete_rows,
                "mental_health_completion_pct": completion_pct,
                "checks": quality_checks,
            },
            "key_findings": key_findings,
            "priority_actions": priority_actions,
            "priority_cohorts": top_cohorts,
            "key_risk_factors": risk_factors,
            "capacity_plan": threshold_plan,
            "capacity_plan_detail": {
                "flagged_n": threshold_plan["flagged_n"],
                "weighted_pct": threshold_plan["flagged_weighted_pct"],
                "mean_score": threshold_plan["mean_flagged_mental_health_score"],
                "delta_vs_baseline_n": threshold_plan["delta_vs_default_threshold_n"],
                "delta_vs_baseline_pct": threshold_plan["delta_vs_threshold_10_pct_point"],
                "recommendation": threshold_plan["recommended_use"],
            },
            "risk_factors": risk_factors,
            "comparison_highlights": comparison_highlights,
            "notes": notes,
            "report_markdown": "\n".join(markdown_lines).strip() + "\n",
        }

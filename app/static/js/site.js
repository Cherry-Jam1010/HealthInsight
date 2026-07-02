const prettyJson = (data) => JSON.stringify(data, null, 2);

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `请求失败: ${response.status}`;
    try {
      const payload = await response.json();
      message = payload?.error?.message || message;
    } catch (error) {
      // Ignore error payload parsing failures and keep a simple fallback.
    }
    throw new Error(message);
  }
  return response.json();
}

function initReveal() {
  const items = document.querySelectorAll(".reveal-on-scroll");
  if (!items.length) return;
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 }
  );
  items.forEach((item) => observer.observe(item));
}

function initMobileNav() {
  const toggle = document.querySelector("[data-nav-toggle]");
  if (!toggle) return;
  toggle.addEventListener("click", () => {
    document.body.classList.toggle("nav-open");
  });
}

const DATASET_META = {
  current: {
    label: "北美 / NHANES",
    branchStatus: "北美当前分支",
    scale: "PHQ-9",
    riskLabel: "PHQ-9 高风险",
    scoreLabel: "平均 PHQ-9",
    referenceLabel: "历史短睡眠率",
    comparisonTitle: "同一类人群，当前风险和历史睡眠背景一起看",
    profileTitle: "当前分组下的 PHQ-9 高风险对比",
    cohortTitle: "当前最值得优先纳入筛查与外展的人群",
    thresholdLabel: "PHQ-9 阈值",
    thresholdMax: 27,
    thresholdDefault: 10,
    comparisonMode: "sleep",
    profileGroups: [
      { value: "age_band", label: "年龄层" },
      { value: "income_band", label: "收入层" },
      { value: "gender", label: "性别" },
      { value: "race_ethnicity", label: "族裔" },
      { value: "education_band", label: "教育层" },
      { value: "sleep_band", label: "睡眠层" },
      { value: "bmi_band", label: "BMI 分层" },
      { value: "chronic_band", label: "慢病负担" },
      { value: "priority_tier", label: "支持优先级" },
    ],
  },
  charls: {
    label: "中国 / CHARLS",
    branchStatus: "中国 CHARLS 分支",
    scale: "CES-D10",
    riskLabel: "CES-D10 高风险",
    scoreLabel: "平均 CES-D10",
    referenceLabel: "北美参考短睡眠率",
    comparisonTitle: "中国分支与北美参考的同维度对照",
    profileTitle: "当前分组下的 CES-D10 高风险对比",
    cohortTitle: "当前最值得优先纳入中国样本筛查与外展的人群",
    thresholdLabel: "CES-D10 阈值",
    thresholdMax: 30,
    thresholdDefault: 10,
    comparisonMode: "risk",
    profileGroups: [
      { value: "age_band", label: "年龄层" },
      { value: "income_band", label: "支出层" },
      { value: "gender", label: "性别" },
      { value: "education_band", label: "教育层" },
      { value: "sleep_band", label: "睡眠层" },
      { value: "chronic_band", label: "慢病负担" },
      { value: "priority_tier", label: "支持优先级" },
      { value: "residence_band", label: "城乡层" },
      { value: "hukou_band", label: "户口层" },
      { value: "mental_health_severity_band", label: "心理健康分层" },
    ],
  },
  custom: {
    label: "自定义 / Sandbox",
    branchStatus: "自定义临时分支",
    scale: "自定义量表",
    riskLabel: "量表高风险",
    scoreLabel: "平均量表得分",
    referenceLabel: "北美参考短睡眠率",
    comparisonTitle: "自定义分支与北美参考的同维度对照",
    profileTitle: "当前分组下的自定义高风险对比",
    cohortTitle: "当前自定义样本里优先筛查与外展的人群",
    thresholdLabel: "量表阈值",
    thresholdMax: 30,
    thresholdDefault: 10,
    comparisonMode: "risk",
    profileGroups: [
      { value: "age_band", label: "年龄层" },
      { value: "income_band", label: "收入层" },
      { value: "gender", label: "性别" },
      { value: "education_band", label: "教育层" },
      { value: "sleep_band", label: "睡眠层" },
      { value: "bmi_band", label: "BMI 分层" },
      { value: "chronic_band", label: "慢病负担" },
      { value: "priority_tier", label: "支持优先级" },
      { value: "residence_band", label: "居住地" },
    ],
  },
};

function getDatasetMeta(dataset) {
  if (typeof dataset === "string" && dataset.startsWith("custom:")) {
    return DATASET_META.custom;
  }
  return DATASET_META[dataset] || DATASET_META.current;
}

function buildApiUrl(path, params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      query.set(key, value);
    }
  });
  const queryString = query.toString();
  return queryString ? `${path}?${queryString}` : path;
}

function formatValue(value, suffix = "") {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return `${value}${suffix}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setButtonState(buttons, expectedValue, getValue) {
  buttons.forEach((button) => {
    button.classList.toggle("is-active", getValue(button) === expectedValue);
  });
}

function setSelectOptions(select, options, currentValue) {
  if (!select) return;
  select.innerHTML = options
    .map((option) => `<option value="${option.value}">${option.label}</option>`)
    .join("");
  const supportedValue = options.some((option) => option.value === currentValue)
    ? currentValue
    : options[0]?.value;
  if (supportedValue) {
    select.value = supportedValue;
  }
}

function createBarRow(row) {
  const group =
    row.group ||
    row.segment_label ||
    `${row.age_band} / ${row.income_band} / ${row.sleep_band}`;
  const rate = row.high_risk_rate_pct ?? row.elevated_priority_rate_pct ?? 0;
  return `
    <div class="bar-item">
      <div class="bar-label">
        <span>${group}</span>
        <strong>${formatValue(rate, "%")}</strong>
      </div>
      <div class="bar-track">
        <div class="bar-fill" style="width:${Math.max(0, Math.min(100, rate || 0))}%"></div>
      </div>
    </div>
  `;
}

function createCohortTitle(row) {
  return row.segment_label || `${row.age_band} / ${row.income_band} / ${row.sleep_band || row.gender}`;
}

function createCohortCard(row, dataset = "current") {
  const meta = getDatasetMeta(dataset);
  const primaryMetric = row.high_risk_rate_pct ?? row.elevated_priority_rate_pct;
  const hasMentalScore = row.mean_mental_health_score != null || row.mean_phq9_score != null;
  const secondaryMetric =
    row.mean_mental_health_score ?? row.mean_phq9_score ?? row.short_sleep_rate_pct;
  const secondaryLabel = hasMentalScore ? meta.scoreLabel : "短睡眠";
  return `
    <article class="cohort-card">
      <div class="cohort-title">${createCohortTitle(row)}</div>
      <div class="cohort-meta">${formatValue(row.participants)} 人样本</div>
      <div class="metric-inline">
        <span>${meta.riskLabel}</span>
        <strong>${formatValue(primaryMetric, "%")}</strong>
      </div>
      <div class="metric-inline">
        <span>${secondaryLabel}</span>
        <strong>${formatValue(secondaryMetric, hasMentalScore ? "" : "%")}</strong>
      </div>
    </article>
  `;
}

function createRiskFactorCard(row) {
  return `
    <article class="cohort-card">
      <div class="cohort-title">${row.dimension} / ${row.group}</div>
      <div class="cohort-meta">${formatValue(row.participants)} 人有效样本</div>
      <div class="metric-inline">
        <span>高风险率</span>
        <strong>${formatValue(row.high_risk_rate_pct, "%")}</strong>
      </div>
      <div class="metric-inline">
        <span>高于总体</span>
        <strong>${formatValue(row.uplift_vs_overall_pct_point, "pt")}</strong>
      </div>
    </article>
  `;
}

function createComparisonCard(row, dataset = "current") {
  const meta = getDatasetMeta(dataset);
  const baselineValue =
    meta.comparisonMode === "risk"
      ? row.baseline_high_risk_rate_pct
      : row.baseline_short_sleep_rate_pct;
  const baselineLabel =
    meta.comparisonMode === "risk" ? "北美参考高风险率" : "历史短睡眠率";

  return `
    <article class="cohort-card">
      <div class="cohort-title">${row.group}</div>
      <div class="cohort-meta">
        当前 ${formatValue(row.current_participants)} 人 / 参考 ${formatValue(row.baseline_participants)} 人
      </div>
      <div class="metric-inline">
        <span>${meta.riskLabel}</span>
        <strong>${formatValue(row.current_high_risk_rate_pct, "%")}</strong>
      </div>
      <div class="metric-inline">
        <span>${baselineLabel}</span>
        <strong>${formatValue(baselineValue, "%")}</strong>
      </div>
    </article>
  `;
}

function initHomeProfileSwitcher() {
  const root = document.querySelector("[data-home-profile]");
  if (!root) return;
  const bars = root.querySelector("[data-profile-bars]");
  const jsonEl = root.querySelector("[data-home-json] code");
  const buttons = document.querySelectorAll("[data-home-group]");

  async function load(group) {
    const data = await fetchJson(
      buildApiUrl("/api/v1/population-profile", {
        group_by: group,
        min_participants: 80,
      })
    );
    const topRows = data.rows.slice(0, 5);
    bars.innerHTML = topRows.map(createBarRow).join("");
    jsonEl.textContent = prettyJson(data);
    root.dataset.currentGroup = group;
    setButtonState(buttons, group, (button) => button.dataset.homeGroup);
  }

  buttons.forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await load(button.dataset.homeGroup);
      } catch (error) {
        jsonEl.textContent = error.message;
      }
    });
  });
}

function initStudio() {
  const root = document.querySelector("[data-studio-root]");
  if (!root) return;

  const state = {
    dataset: "current",
    comparisonGroup: "age_band",
  };

  const form = root.querySelector("[data-profile-form]");
  const groupSelect = form.querySelector('select[name="group_by"]');
  const bars = root.querySelector("[data-profile-bars]");
  const status = root.querySelector("[data-profile-status]");
  const jsonCode = root.querySelector("[data-live-json] code");
  const endpointLabel = root.querySelector("[data-endpoint-label]");
  const endpointButtons = root.querySelectorAll("[data-endpoint-key]");
  const datasetButtons = root.querySelectorAll("[data-dataset-button]");
  const datasetStatus = root.querySelector("[data-dataset-status]");
  const cohortBoard = root.querySelector("[data-cohort-board]");
  const riskFactorBoard = root.querySelector("[data-risk-factor-board]");
  const thresholdForm = root.querySelector("[data-threshold-form]");
  const thresholdInput = thresholdForm?.querySelector('input[name="threshold"]');
  const thresholdStatus = root.querySelector("[data-threshold-status]");
  const thresholdJson = root.querySelector("[data-threshold-json] code");
  const thresholdFlaggedN = root.querySelector("[data-threshold-flagged-n]");
  const thresholdFlaggedPct = root.querySelector("[data-threshold-flagged-pct]");
  const thresholdWeeks = root.querySelector("[data-threshold-weeks]");
  const thresholdDelta = root.querySelector("[data-threshold-delta]");
  const comparisonBoard = root.querySelector("[data-cycle-comparison-board]");
  const comparisonJson = root.querySelector("[data-cycle-json] code");
  const comparisonButtons = root.querySelectorAll("[data-cycle-group]");
  const summaryShort = root.querySelector("[data-summary-short-sleep]");
  const summarySedentary = root.querySelector("[data-summary-sedentary]");
  const summaryElevated = root.querySelector("[data-summary-elevated]");
  const summaryRows = root.querySelector("[data-summary-rows]");
  const summaryHighRiskLabel = root.querySelector("[data-summary-high-risk-label]");
  const summaryScoreLabel = root.querySelector("[data-summary-score-label]");
  const summaryCompareLabel = root.querySelector("[data-summary-compare-label]");
  const summaryThresholdLabel = root.querySelector("[data-summary-threshold-label]");
  const profileTitle = root.querySelector("[data-profile-title]");
  const cohortTitle = root.querySelector("[data-cohort-title]");
  const comparisonTitle = root.querySelector("[data-comparison-title]");
  const thresholdInputLabel = root.querySelector("[data-threshold-input-label]");

  function getMeta() {
    return getDatasetMeta(state.dataset);
  }

  function buildStudioEndpoint(key) {
    switch (key) {
      case "summary":
        return buildApiUrl("/api/v1/summary", { dataset: state.dataset });
      case "profile":
        return buildApiUrl("/api/v1/population-profile", {
          dataset: state.dataset,
          group_by: groupSelect.value,
          min_participants: form.querySelector('input[name="min_participants"]').value,
          min_age: form.querySelector('input[name="min_age"]').value,
          max_age: form.querySelector('input[name="max_age"]').value,
        });
      case "priority-cohorts":
        return buildApiUrl("/api/v1/priority-cohorts", {
          dataset: state.dataset,
          limit: 6,
          min_participants: 100,
        });
      case "risk-factors":
        return buildApiUrl("/api/v1/risk-factors", {
          dataset: state.dataset,
          limit: 6,
          min_participants: 120,
        });
      case "cycle-comparison":
        return buildApiUrl("/api/v1/cycle-comparison", {
          dataset: state.dataset,
          group_by: state.comparisonGroup,
          min_participants: 80,
        });
      case "threshold-simulate":
        return buildApiUrl("/api/v1/threshold-simulate", {
          dataset: state.dataset,
          threshold: thresholdInput?.value || getMeta().thresholdDefault,
          weekly_capacity:
            thresholdForm?.querySelector('input[name="weekly_capacity"]')?.value || 20,
        });
      default:
        return buildApiUrl("/api/v1/summary", { dataset: state.dataset });
    }
  }

  function applyDatasetMeta() {
    const meta = getMeta();
    datasetStatus.textContent = meta.branchStatus;
    summaryHighRiskLabel.textContent = meta.riskLabel;
    summaryScoreLabel.textContent = meta.scoreLabel;
    summaryCompareLabel.textContent = meta.referenceLabel;
    summaryThresholdLabel.textContent = "阈值10筛出率";
    profileTitle.textContent = meta.profileTitle;
    cohortTitle.textContent = meta.cohortTitle;
    comparisonTitle.textContent = meta.comparisonTitle;
    thresholdInputLabel.textContent = meta.thresholdLabel;
    thresholdInput.max = String(meta.thresholdMax);
    if (Number(thresholdInput.value) > meta.thresholdMax) {
      thresholdInput.value = String(meta.thresholdDefault);
    }
    setSelectOptions(groupSelect, meta.profileGroups, groupSelect.value);
    setButtonState(datasetButtons, state.dataset, (button) => button.dataset.datasetButton);
  }

  async function refreshSummary() {
    const data = await fetchJson(buildApiUrl("/api/v1/summary", { dataset: state.dataset }));
    summaryShort.textContent = formatValue(data.mental_health_signals.phq_high_risk_rate_pct, "%");
    summarySedentary.textContent = formatValue(data.mental_health_signals.mean_phq9_score);
    summaryElevated.textContent = formatValue(data.shared_signals.legacy_short_sleep_rate_pct, "%");
    summaryRows.textContent = formatValue(data.threshold_reference.flagged_weighted_pct, "%");
  }

  async function refreshProfile(formData) {
    const params = Object.fromEntries(formData.entries());
    params.dataset = state.dataset;
    const endpoint = buildApiUrl("/api/v1/population-profile", params);
    status.textContent = "加载中";
    endpointLabel.textContent = endpoint;
    const data = await fetchJson(endpoint);
    bars.innerHTML = data.rows.slice(0, 8).map(createBarRow).join("");
    jsonCode.textContent = prettyJson(data);
    status.textContent = "已更新";
    setButtonState(endpointButtons, "profile", (button) => button.dataset.endpointKey);
  }

  async function refreshCohorts() {
    const data = await fetchJson(
      buildApiUrl("/api/v1/priority-cohorts", {
        dataset: state.dataset,
        limit: 6,
        min_participants: 100,
      })
    );
    cohortBoard.innerHTML = data.rows.map((row) => createCohortCard(row, state.dataset)).join("");
  }

  async function refreshRiskFactors() {
    if (!riskFactorBoard) return;
    const data = await fetchJson(
      buildApiUrl("/api/v1/risk-factors", {
        dataset: state.dataset,
        limit: 6,
        min_participants: 120,
      })
    );
    riskFactorBoard.innerHTML = data.rows.map(createRiskFactorCard).join("");
  }

  async function refreshComparison(group = state.comparisonGroup) {
    if (!comparisonBoard || !comparisonJson) return;
    state.comparisonGroup = group;
    const endpoint = buildApiUrl("/api/v1/cycle-comparison", {
      dataset: state.dataset,
      group_by: group,
      min_participants: 80,
    });
    const data = await fetchJson(endpoint);
    comparisonBoard.innerHTML = data.rows
      .slice(0, 6)
      .map((row) => createComparisonCard(row, state.dataset))
      .join("");
    comparisonJson.textContent = prettyJson(data);
    setButtonState(comparisonButtons, group, (button) => button.dataset.cycleGroup);
  }

  async function refreshThreshold(formData) {
    if (!thresholdForm || !thresholdJson) return;
    const params = Object.fromEntries(formData.entries());
    params.dataset = state.dataset;
    const endpoint = buildApiUrl("/api/v1/threshold-simulate", params);
    thresholdStatus.textContent = "模拟中";
    const data = await fetchJson(endpoint);
    thresholdFlaggedN.textContent = formatValue(data.flagged_n);
    thresholdFlaggedPct.textContent = formatValue(data.flagged_weighted_pct, "%");
    thresholdWeeks.textContent = formatValue(data.estimated_counselor_weeks);
    thresholdDelta.textContent = formatValue(data.delta_vs_threshold_10_pct_point, "pt");
    thresholdJson.textContent = prettyJson(data);
    thresholdStatus.textContent = `阈值 ${data.threshold}`;
  }

  async function loadEndpointKey(key) {
    const endpoint = buildStudioEndpoint(key);
    endpointLabel.textContent = endpoint;
    const data = await fetchJson(endpoint);
    jsonCode.textContent = prettyJson(data);
    setButtonState(endpointButtons, key, (button) => button.dataset.endpointKey);
  }

  async function reloadStudioBranch() {
    applyDatasetMeta();
    await Promise.all([
      refreshSummary(),
      refreshProfile(new FormData(form)),
      refreshCohorts(),
      refreshRiskFactors(),
      refreshComparison(state.comparisonGroup),
      refreshThreshold(new FormData(thresholdForm)),
    ]);
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await refreshProfile(new FormData(form));
    } catch (error) {
      status.textContent = "加载失败";
      jsonCode.textContent = error.message;
    }
  });

  endpointButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await loadEndpointKey(button.dataset.endpointKey);
      } catch (error) {
        jsonCode.textContent = error.message;
      }
    });
  });

  datasetButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      state.dataset = button.dataset.datasetButton;
      try {
        await reloadStudioBranch();
      } catch (error) {
        status.textContent = "切换失败";
        jsonCode.textContent = error.message;
      }
    });
  });

  root.querySelector("[data-refresh-cohorts]")?.addEventListener("click", async () => {
    try {
      await refreshCohorts();
    } catch (error) {
      cohortBoard.innerHTML = `<article class="cohort-card"><strong>${error.message}</strong></article>`;
    }
  });

  thresholdForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await refreshThreshold(new FormData(thresholdForm));
    } catch (error) {
      thresholdStatus.textContent = "模拟失败";
      thresholdJson.textContent = error.message;
    }
  });

  comparisonButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await refreshComparison(button.dataset.cycleGroup);
      } catch (error) {
        comparisonJson.textContent = error.message;
      }
    });
  });

  applyDatasetMeta();
  reloadStudioBranch().catch(() => {});
}

function initReports() {
  const root = document.querySelector("[data-report-root]");
  if (!root) return;

  const state = {
    dataset: "current",
    audience: "researcher",
  };

  const audienceButtons = root.querySelectorAll("[data-audience]");
  const datasetButtons = root.querySelectorAll("[data-report-dataset-button]");
  const branchStatus = root.querySelector("[data-report-branch-status]");
  const headline = root.querySelector("[data-report-headline]");
  const focus = root.querySelector("[data-report-focus]");
  const notes = root.querySelector("[data-report-notes]");
  const cohorts = root.querySelector("[data-report-cohorts]");
  const endpoint = root.querySelector("[data-report-endpoint]");
  const jsonCode = root.querySelector("[data-report-json] code");

  async function loadReport() {
    const meta = getDatasetMeta(state.dataset);
    branchStatus.textContent = meta.branchStatus;
    const url = buildApiUrl(`/api/v1/reports/${state.audience}`, { dataset: state.dataset });
    const data = await fetchJson(url);
    headline.textContent = data.headline;
    focus.innerHTML = data.focus_points.map((item) => `<li>${item}</li>`).join("");
    notes.innerHTML = data.shared_notes.map((item) => `<li>${item}</li>`).join("");
    cohorts.innerHTML = data.top_cohorts
      .map((row) => createCohortCard(row, state.dataset))
      .join("");
    endpoint.textContent = url;
    jsonCode.textContent = prettyJson(data);
    setButtonState(audienceButtons, state.audience, (button) => button.dataset.audience);
    setButtonState(datasetButtons, state.dataset, (button) => button.dataset.reportDatasetButton);
  }

  audienceButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      state.audience = button.dataset.audience;
      try {
        await loadReport();
      } catch (error) {
        jsonCode.textContent = error.message;
      }
    });
  });

  datasetButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      state.dataset = button.dataset.reportDatasetButton;
      try {
        await loadReport();
      } catch (error) {
        jsonCode.textContent = error.message;
      }
    });
  });

  loadReport().catch(() => {});
}

function initWorkbench() {
  const root = document.querySelector("[data-workbench-root]");
  if (!root) return;

  const state = {
    selectedDataset: null,
    manualRows: [],
  };

  const syntheticForm = root.querySelector("[data-synthetic-form]");
  const manualRowForm = root.querySelector("[data-manual-row-form]");
  const manualDatasetForm = root.querySelector("[data-manual-dataset-form]");
  const manualRowsEl = root.querySelector("[data-manual-rows]");
  const manualCount = root.querySelector("[data-manual-count]");
  const clearManualButton = root.querySelector("[data-manual-clear]");
  const datasetList = root.querySelector("[data-custom-dataset-list]");
  const status = root.querySelector("[data-workbench-status]");
  const labelEl = root.querySelector("[data-workbench-label]");
  const highRiskEl = root.querySelector("[data-workbench-high-risk]");
  const scoreEl = root.querySelector("[data-workbench-score]");
  const sleepEl = root.querySelector("[data-workbench-sleep]");
  const cohortsEl = root.querySelector("[data-workbench-cohorts]");
  const riskFactorsEl = root.querySelector("[data-workbench-risk-factors]");
  const reportHeadline = root.querySelector("[data-workbench-report-headline]");
  const reportFocus = root.querySelector("[data-workbench-report-focus]");
  const jsonCode = root.querySelector("[data-workbench-json] code");

  function renderManualRows() {
    manualCount.textContent = `${state.manualRows.length} 行`;
    if (!state.manualRows.length) {
      manualRowsEl.innerHTML =
        '<article class="manual-row-card"><strong>还没有手工样本</strong><span>先用左侧表单添加几行，凑够 3 行就能生成一个临时分支。</span></article>';
      return;
    }
    manualRowsEl.innerHTML = state.manualRows
      .map(
        (row, index) => `
          <article class="manual-row-card">
            <strong>样本 ${index + 1}</strong>
            <span>
              年龄 ${escapeHtml(row.age)} / ${escapeHtml(row.gender)} / 睡眠 ${escapeHtml(row.sleep_hours)}h /
              ${escapeHtml(row.income_band)} / 慢病 ${escapeHtml(row.chronic_condition_count)} / 分数 ${escapeHtml(row.mental_health_score)}
            </span>
          </article>
        `
      )
      .join("");
  }

  function renderDatasetList(catalog, selectedDataset = state.selectedDataset) {
    const datasets = catalog?.datasets || [];
    if (!datasets.length) {
      datasetList.innerHTML = '<span class="status-dot muted-status">生成后会显示在这里</span>';
      return;
    }
    datasetList.innerHTML = datasets
      .map(
        (item) => `
          <button
            class="endpoint-pick ${item.id === selectedDataset ? "is-active" : ""}"
            type="button"
            data-custom-dataset="${escapeHtml(item.id)}"
          >
            ${escapeHtml(item.label)} · ${escapeHtml(item.scale)}
          </button>
        `
      )
      .join("");

    datasetList.querySelectorAll("[data-custom-dataset]").forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          await loadDataset(button.dataset.customDataset);
        } catch (error) {
          status.textContent = error.message;
          jsonCode.textContent = error.message;
        }
      });
    });
  }

  async function refreshCatalog(preferredDataset = state.selectedDataset) {
    const catalog = await fetchJson("/api/v1/custom-datasets");
    renderDatasetList(catalog, preferredDataset);
    if (!preferredDataset && catalog.datasets?.length) {
      await loadDataset(catalog.datasets[0].id);
    }
    return catalog;
  }

  async function loadDataset(datasetId) {
    state.selectedDataset = datasetId;
    status.textContent = "正在加载临时分支";
    const [summary, cohorts, riskFactors, report] = await Promise.all([
      fetchJson(buildApiUrl("/api/v1/summary", { dataset: datasetId })),
      fetchJson(
        buildApiUrl("/api/v1/priority-cohorts", {
          dataset: datasetId,
          limit: 6,
          min_participants: 3,
        })
      ),
      fetchJson(
        buildApiUrl("/api/v1/risk-factors", {
          dataset: datasetId,
          limit: 6,
          min_participants: 3,
        })
      ),
      fetchJson(buildApiUrl("/api/v1/reports/researcher", { dataset: datasetId })),
    ]);

    labelEl.textContent = summary.selected_branch.label;
    highRiskEl.textContent = formatValue(summary.mental_health_signals.high_risk_rate_pct, "%");
    scoreEl.textContent = formatValue(summary.mental_health_signals.mean_score);
    sleepEl.textContent = formatValue(summary.shared_signals.current_short_sleep_rate_pct, "%");
    cohortsEl.innerHTML = cohorts.rows.length
      ? cohorts.rows.map((row) => createCohortCard(row, datasetId)).join("")
      : '<article class="cohort-card"><strong>样本还太少</strong><p>再增加几行，重点人群组合会更稳定。</p></article>';
    riskFactorsEl.innerHTML = riskFactors.rows.length
      ? riskFactors.rows.map(createRiskFactorCard).join("")
      : '<article class="cohort-card"><strong>分层还不够丰富</strong><p>补充更多年龄、睡眠和收入差异后，这里会出现更有解释力的结果。</p></article>';
    reportHeadline.textContent = report.headline;
    reportFocus.innerHTML = report.focus_points.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    jsonCode.textContent = prettyJson(summary);
    status.textContent = `当前分支: ${summary.selected_branch.label}`;
    await refreshCatalog(datasetId);
  }

  syntheticForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    status.textContent = "正在生成演示分支";
    try {
      const formData = new FormData(syntheticForm);
      const payload = Object.fromEntries(formData.entries());
      if (!payload.seed) {
        delete payload.seed;
      } else {
        payload.seed = Number(payload.seed);
      }
      payload.sample_size = Number(payload.sample_size);
      const response = await fetchJson("/api/v1/custom-datasets/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await loadDataset(response.dataset.id);
    } catch (error) {
      status.textContent = "生成失败";
      jsonCode.textContent = error.message;
    }
  });

  manualRowForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    const row = Object.fromEntries(new FormData(manualRowForm).entries());
    row.age = Number(row.age);
    row.sleep_hours = Number(row.sleep_hours);
    row.bmi = row.bmi === "" ? null : Number(row.bmi);
    row.chronic_condition_count = Number(row.chronic_condition_count);
    row.mental_health_score = Number(row.mental_health_score);
    row.weight = Number(row.weight);
    state.manualRows.push(row);
    renderManualRows();
    status.textContent = `已添加 ${state.manualRows.length} 行手工样本`;
  });

  manualDatasetForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (state.manualRows.length < 3) {
      status.textContent = "至少先添加 3 行手工样本";
      return;
    }
    status.textContent = "正在生成手工分支";
    try {
      const formValues = Object.fromEntries(new FormData(manualDatasetForm).entries());
      const response = await fetchJson("/api/v1/custom-datasets/manual", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formValues.name,
          scale: formValues.scale,
          rows: state.manualRows,
        }),
      });
      state.manualRows = [];
      renderManualRows();
      await loadDataset(response.dataset.id);
    } catch (error) {
      status.textContent = "生成失败";
      jsonCode.textContent = error.message;
    }
  });

  clearManualButton?.addEventListener("click", () => {
    state.manualRows = [];
    renderManualRows();
    status.textContent = "已清空手工样本列表";
  });

  renderManualRows();
  refreshCatalog().catch(() => {});
}

function initExamples() {
  const root = document.querySelector("[data-example-root]");
  if (!root) return;

  const examples = {
    community: {
      badge: "机构运营场景",
      title: "市级心理健康中心如何识别优先筛查人群",
      summary:
        "团队需要在有限预算下安排下一轮筛查与外展服务，希望先看清哪些群体同时呈现 PHQ-9 高风险、睡眠不足和低收入信号。",
      tags: ["PHQ-9 风险分层", "筛查优先级排序", "管理汇报摘要"],
      steps: [
        ["读取样本", "先从人口学、PHQ-9、睡眠、BMI 和慢病数据里建立分析基础。"],
        ["识别重点群体", "按年龄、收入和睡眠压力定位优先筛查对象。"],
        ["生成机构简报", "把 PHQ-9 风险结果整理成管理团队能快速理解的语言。"],
      ],
      outcomeTitle: "一份可直接进入周会讨论的优先级名单",
      outcomes: [
        "优先筛查群体组合列表",
        "PHQ-9 高风险占比与说明",
        "适合管理层阅读的摘要语言",
      ],
      endpoints: ["/api/v1/priority-cohorts", "/api/v1/reports/manager"],
    },
    campus: {
      badge: "学生服务场景",
      title: "高校学生支持中心如何提前发现高压力生活方式人群",
      summary:
        "学校希望在学期中段提前锁定 PHQ-9 风险更高、睡眠不足、需要重点触达的学生群体，用于安排宣传、筛查与支持服务。",
      tags: ["学生支持", "学期筛查计划", "触达策略优化"],
      steps: [
        ["分层查看画像", "先看不同年龄段与群体的 PHQ-9 风险差异。"],
        ["圈定重点对象", "识别高风险占比更高的学生人群组合。"],
        ["输出行动建议", "形成适合学生事务部门使用的外展与沟通节奏。"],
      ],
      outcomeTitle: "一套更适合校园支持体系的触达优先级建议",
      outcomes: [
        "不同群体的风险分层画面",
        "更适合校内汇报的轻量简报",
        "支持下一轮学生筛查活动设计",
      ],
      endpoints: ["/api/v1/population-profile", "/api/v1/reports/clinical"],
    },
    hospital: {
      badge: "医院管理场景",
      title: "医院运营团队如何更快看见哪些群体需要优先投入服务资源",
      summary:
        "医院管理部门希望用更短时间理解 PHQ-9 风险更高的群体组合，把服务量能、宣教资源和筛查安排投向更需要的对象。",
      tags: ["资源配置", "运营汇报", "服务优先级"],
      steps: [
        ["汇总总体信号", "先确认 PHQ-9 高风险率和阈值筛出比例等全局指标。"],
        ["锁定重点组合", "查看当前样本里最值得优先关注的人群组合。"],
        ["支持跨部门沟通", "让管理、临床和项目团队共享同一份结论框架。"],
      ],
      outcomeTitle: "一个适合运营例会和项目协调的共享决策面板",
      outcomes: [
        "服务优先级分层依据",
        "重点对象及说明口径",
        "跨管理与执行团队共用的结果入口",
      ],
      endpoints: ["/api/v1/summary", "/api/v1/priority-cohorts", "/api/v1/reports/manager"],
    },
  };

  const buttons = root.querySelectorAll("[data-example-button]");
  const title = root.querySelector("[data-example-title]");
  const badge = root.querySelector("[data-example-badge]");
  const summary = root.querySelector("[data-example-summary]");
  const tags = root.querySelector("[data-example-tags]");
  const steps = root.querySelector("[data-example-steps]");
  const outcomeTitle = root.querySelector("[data-example-outcome-title]");
  const outcomes = root.querySelector("[data-example-outcomes]");
  const endpoints = root.querySelector("[data-example-endpoints]");

  function renderStep([label, text], index) {
    return `
      <article>
        <span>Step ${index + 1}</span>
        <h3>${label}</h3>
        <p>${text}</p>
      </article>
    `;
  }

  function loadExample(key) {
    const item = examples[key];
    if (!item) return;
    title.textContent = item.title;
    badge.textContent = item.badge;
    summary.textContent = item.summary;
    outcomeTitle.textContent = item.outcomeTitle;
    tags.innerHTML = item.tags.map((entry) => `<span>${entry}</span>`).join("");
    steps.innerHTML = item.steps.map(renderStep).join("");
    outcomes.innerHTML = item.outcomes.map((entry) => `<li>${entry}</li>`).join("");
    endpoints.innerHTML = item.endpoints.map((entry) => `<span>${entry}</span>`).join("");
    buttons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.exampleButton === key);
    });
  }

  buttons.forEach((button) => {
    button.addEventListener("click", () => loadExample(button.dataset.exampleButton));
  });

  loadExample("community");
}

function initVisionMap() {
  const root = document.querySelector("[data-vision-root]");
  if (!root) return;

  const regions = {
    north_america: {
      stage: "当前起点",
      title: "北美机构级样本洞察",
      description:
        "以现有 NHANES 数据能力为核心，持续验证重点群体识别、机构汇报与筛查支持这条主线。",
      points: [
        "公共卫生与心理健康项目的机构级分析",
        "行为与睡眠信号驱动的优先级识别",
        "多角色汇报与 API 对接能力",
      ],
    },
    europe: {
      stage: "下一阶段",
      title: "欧洲多机构协作与可比性分析",
      description:
        "未来会支持不同机构之间的口径统一，帮助研究网络和城市级服务体系进行横向比较。",
      points: [
        "跨城市或跨机构的画像对照",
        "更标准化的指标解释与汇报模板",
        "支持项目合作与联合研究展示",
      ],
    },
    mena: {
      stage: "区域扩展",
      title: "中东与非洲的服务可及性视角",
      description:
        "除了行为信号，我们希望逐步补入服务可及性、资源分布和干预落地条件等更贴近现实的变量。",
      points: [
        "服务供给与覆盖缺口识别",
        "项目优先落地区域判断",
        "更贴近公共卫生资源规划的输出",
      ],
    },
    asia_pacific: {
      stage: "全球产品化",
      title: "亚太多语言、多校园、多医院网络支持",
      description:
        "亚太扩展会强调多语言表达、本地化汇报和不同机构类型之间的可复用产品模板。",
      points: [
        "中文、英文等多语言展示能力",
        "高校、医院、机构网络的复用模板",
        "区域级趋势与项目响应对照",
      ],
    },
    latin_america: {
      stage: "合作试点",
      title: "拉美地区社区项目与外展支持",
      description:
        "面向社区外展和基层服务体系，平台会强调轻量化简报、可解释信号和便于协同的重点对象清单。",
      points: [
        "社区级重点群体排序",
        "更轻量的项目汇报输出",
        "支持外展与触达活动规划",
      ],
    },
  };

  const buttons = root.querySelectorAll("[data-region-button]");
  const stage = root.querySelector("[data-region-stage]");
  const title = root.querySelector("[data-region-title]");
  const description = root.querySelector("[data-region-description]");
  const points = root.querySelector("[data-region-points]");

  function loadRegion(key) {
    const item = regions[key];
    if (!item) return;
    stage.textContent = item.stage;
    title.textContent = item.title;
    description.textContent = item.description;
    points.innerHTML = item.points.map((entry) => `<li>${entry}</li>`).join("");
    buttons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.regionButton === key);
    });
  }

  buttons.forEach((button) => {
    button.addEventListener("click", () => loadRegion(button.dataset.regionButton));
  });

  loadRegion("north_america");
}

document.addEventListener("DOMContentLoaded", () => {
  initMobileNav();
  initReveal();
  initHomeProfileSwitcher();
  initStudio();
  initReports();
  initWorkbench();
  initExamples();
  initVisionMap();
});

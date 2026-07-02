function opPrettyJson(data) {
  return JSON.stringify(data, null, 2);
}

async function opFetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    let payload = null;
    try {
      payload = await response.json();
      message = payload?.error?.message || message;
    } catch (error) {
      // Keep fallback message when payload is not JSON.
    }
    const enrichedError = new Error(message);
    enrichedError.status = response.status;
    enrichedError.payload = payload;
    throw enrichedError;
  }
  return response.json();
}

function opBuildUrl(path, params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, value);
    }
  });
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

function opFormatValue(value, suffix = "") {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return `${value}${suffix}`;
}

function opEscapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function opSetButtonState(buttons, expectedValue, getValue) {
  buttons.forEach((button) => {
    button.classList.toggle("is-active", getValue(button) === expectedValue);
  });
}

function opDatasetMeta(dataset) {
  if (dataset && String(dataset).startsWith("custom:")) {
    return { label: "机构导入数据", status: "当前使用临时机构数据集" };
  }
  if (dataset === "charls") {
    return { label: "中国 / CHARLS", status: "当前使用中国 CHARLS 分支" };
  }
  return { label: "北美 / NHANES", status: "当前使用北美 NHANES 分支" };
}

function opCreateCohortCard(row) {
  return `
    <article class="cohort-card">
      <div class="cohort-title">${opEscapeHtml(row.segment_label || row.group || "-")}</div>
      <div class="cohort-meta">${opFormatValue(row.participants)} 人样本</div>
      <div class="metric-inline">
        <span>高风险占比</span>
        <strong>${opFormatValue(row.high_risk_rate_pct, "%")}</strong>
      </div>
      <div class="metric-inline">
        <span>平均量表分</span>
        <strong>${opFormatValue(row.mean_mental_health_score ?? row.mean_phq9_score)}</strong>
      </div>
    </article>
  `;
}

function opCreateRiskFactorCard(row) {
  return `
    <article class="cohort-card">
      <div class="cohort-title">${opEscapeHtml(row.dimension)} / ${opEscapeHtml(row.group)}</div>
      <div class="cohort-meta">${opFormatValue(row.participants)} 人样本</div>
      <div class="metric-inline">
        <span>高风险占比</span>
        <strong>${opFormatValue(row.high_risk_rate_pct, "%")}</strong>
      </div>
      <div class="metric-inline">
        <span>高于总体</span>
        <strong>${opFormatValue(row.uplift_vs_overall_pct_point, "pt")}</strong>
      </div>
    </article>
  `;
}

function opCreateInsightCard(item) {
  const subtitle = item.owner && item.timeline ? `${item.owner} / ${item.timeline}` : item.title;
  return `
    <article class="insight-card">
      <strong>${opEscapeHtml(item.title || "-")}</strong>
      ${subtitle && subtitle !== item.title ? `<span>${opEscapeHtml(subtitle)}</span>` : ""}
      <p>${opEscapeHtml(item.detail || "")}</p>
    </article>
  `;
}

function opCreateQualityCard(item) {
  return `
    <article class="insight-card">
      <strong>${opEscapeHtml(item.label)}</strong>
      <span>${opFormatValue(item.value_pct, "%")}</span>
      <p>${opEscapeHtml(item.status)}</p>
    </article>
  `;
}

function opDownloadText(filename, content) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function isCustomDatasetId(dataset) {
  return typeof dataset === "string" && dataset.startsWith("custom:");
}

async function fetchCustomDatasetCatalog() {
  return opFetchJson("/api/v1/custom-datasets");
}

function customDatasetExists(catalog, datasetId) {
  return (catalog?.datasets || []).some((item) => item.id === datasetId);
}

function isMissingCustomDatasetError(error) {
  return (
    error instanceof Error &&
    typeof error.message === "string" &&
    error.message.toLowerCase().includes("custom dataset not found")
  );
}

function isMinParticipantsValidationError(error, fallbackMin = 20) {
  const details = error?.payload?.error?.details?.errors;
  if (!Array.isArray(details)) {
    return false;
  }
  return details.some(
    (item) =>
      item?.loc?.includes?.("min_participants") &&
      item?.ctx?.ge === fallbackMin
  );
}

function withMinParticipants(url, minParticipants) {
  const parsed = new URL(url, window.location.origin);
  parsed.searchParams.set("min_participants", String(minParticipants));
  return `${parsed.pathname}${parsed.search}`;
}

async function opFetchJsonWithMinParticipantsFallback(url, options = {}, fallbackMin = 20) {
  try {
    return await opFetchJson(url, options);
  } catch (error) {
    const parsed = new URL(url, window.location.origin);
    const requestedMin = Number(parsed.searchParams.get("min_participants"));
    if (
      Number.isFinite(requestedMin) &&
      requestedMin < fallbackMin &&
      isMinParticipantsValidationError(error, fallbackMin)
    ) {
      return opFetchJson(withMinParticipants(url, fallbackMin), options);
    }
    throw error;
  }
}

function initOperationalWorkbench() {
  const root = document.querySelector("[data-practical-workbench-root]");
  if (!root) return;

  const state = {
    selectedDataset: null,
    manualRows: [],
    lastReport: null,
  };

  const uploadForm = root.querySelector("[data-upload-form]");
  const uploadFileInput = root.querySelector("[data-upload-file]");
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
  const reportActions = root.querySelector("[data-workbench-actions]");
  const qualityEl = root.querySelector("[data-workbench-quality]");
  const exportButton = root.querySelector("[data-workbench-export-report]");
  const jsonCode = root.querySelector("[data-workbench-json] code");

  function renderManualRows() {
    manualCount.textContent = `${state.manualRows.length} 行`;
    if (!state.manualRows.length) {
      manualRowsEl.innerHTML =
        '<article class="manual-row-card"><strong>还没有手工样本</strong><span>先录入几行样本，凑够 3 行后就可以生成临时数据集。</span></article>';
      return;
    }
    manualRowsEl.innerHTML = state.manualRows
      .map(
        (row, index) => `
          <article class="manual-row-card">
            <strong>样本 ${index + 1}</strong>
            <span>年龄 ${opEscapeHtml(row.age)} / ${opEscapeHtml(row.gender)} / 睡眠 ${opEscapeHtml(row.sleep_hours)}h / ${opEscapeHtml(row.income_band)} / 分数 ${opEscapeHtml(row.mental_health_score)}</span>
          </article>
        `
      )
      .join("");
  }

  function renderDatasetList(catalog) {
    const datasets = catalog?.datasets || [];
    if (!datasets.length) {
      datasetList.innerHTML = '<span class="status-dot muted-status">导入或生成后会显示在这里</span>';
      return;
    }
    datasetList.innerHTML = datasets
      .map(
        (item) => `
          <button class="endpoint-pick ${item.id === state.selectedDataset ? "is-active" : ""}" type="button" data-custom-dataset="${opEscapeHtml(item.id)}">
            ${opEscapeHtml(item.label)} · ${opEscapeHtml(item.scale)}
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
        }
      });
    });
  }

  async function refreshCatalog(preferredDataset = state.selectedDataset) {
    const catalog = await fetchCustomDatasetCatalog();
    if (preferredDataset) {
      state.selectedDataset = preferredDataset;
    }
    renderDatasetList(catalog);
    if (!state.selectedDataset && catalog.datasets?.length) {
      await loadDataset(catalog.datasets[0].id);
    }
  }

  async function handleMissingCustomDataset(datasetId) {
    const catalog = await fetchCustomDatasetCatalog();
    state.selectedDataset = null;
    renderDatasetList(catalog);
    status.textContent = `临时数据集 ${datasetId} 已失效，通常是因为服务重启。请重新导入或重新生成。`;
    jsonCode.textContent = "custom dataset no longer exists on the server";
  }

  async function loadDataset(datasetId) {
    const catalog = await fetchCustomDatasetCatalog();
    if (isCustomDatasetId(datasetId) && !customDatasetExists(catalog, datasetId)) {
      await handleMissingCustomDataset(datasetId);
      return;
    }

    state.selectedDataset = datasetId;
    renderDatasetList(catalog);
    status.textContent = "正在加载机构数据集";
    let summary;
    let cohorts;
    let riskFactors;
    let report;
    try {
      [summary, cohorts, riskFactors, report] = await Promise.all([
        opFetchJson(opBuildUrl("/api/v1/summary", { dataset: datasetId })),
        opFetchJsonWithMinParticipantsFallback(
          opBuildUrl("/api/v1/priority-cohorts", {
            dataset: datasetId,
            limit: 6,
            min_participants: 3,
          })
        ),
        opFetchJsonWithMinParticipantsFallback(
          opBuildUrl("/api/v1/risk-factors", {
            dataset: datasetId,
            limit: 6,
            min_participants: 3,
          })
        ),
        opFetchJson(
          opBuildUrl("/api/v1/institution-report", {
            dataset: datasetId,
            audience: "manager",
            organization_name: "当前机构",
            weekly_capacity: 20,
          })
        ),
      ]);
    } catch (error) {
      if (isCustomDatasetId(datasetId) && isMissingCustomDatasetError(error)) {
        await handleMissingCustomDataset(datasetId);
        return;
      }
      throw error;
    }

    state.lastReport = report;
    labelEl.textContent = summary.selected_branch.label;
    highRiskEl.textContent = opFormatValue(summary.mental_health_signals.high_risk_rate_pct, "%");
    scoreEl.textContent = opFormatValue(summary.mental_health_signals.mean_score);
    sleepEl.textContent = opFormatValue(summary.shared_signals.current_short_sleep_rate_pct, "%");
    cohortsEl.innerHTML = cohorts.rows.length
      ? cohorts.rows.map(opCreateCohortCard).join("")
      : '<article class="cohort-card"><strong>样本量还偏小</strong><p>继续补充样本后，重点人群会更稳定。</p></article>';
    riskFactorsEl.innerHTML = riskFactors.rows.length
      ? riskFactors.rows.map(opCreateRiskFactorCard).join("")
      : '<article class="cohort-card"><strong>分层暂不稳定</strong><p>建议再补充年龄、收入和睡眠差异较大的样本。</p></article>';
    reportHeadline.textContent = report.report_title;
    reportFocus.innerHTML = report.executive_summary.map((item) => `<li>${opEscapeHtml(item)}</li>`).join("");
    reportActions.innerHTML = report.priority_actions.map(opCreateInsightCard).join("");
    qualityEl.innerHTML = report.data_quality.checks.map(opCreateQualityCard).join("");
    jsonCode.textContent = opPrettyJson(summary);
    status.textContent = `当前数据集: ${summary.selected_branch.label}`;
    await refreshCatalog(datasetId);
  }

  uploadForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = uploadFileInput?.files?.[0];
    if (!file) {
      status.textContent = "请先选择一个 CSV 文件";
      return;
    }
    status.textContent = "正在导入机构 CSV";
    try {
      const csvContent = await file.text();
      const formData = new FormData(uploadForm);
      const payload = {
        name: formData.get("name"),
        scale: formData.get("scale"),
        csv_content: csvContent,
      };
      const response = await opFetchJson("/api/v1/custom-datasets/upload-csv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      uploadForm.reset();
      await loadDataset(response.dataset.id);
    } catch (error) {
      status.textContent = "CSV 导入失败";
      jsonCode.textContent = error.message;
    }
  });

  syntheticForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    status.textContent = "正在生成演示数据集";
    try {
      const formData = new FormData(syntheticForm);
      const payload = Object.fromEntries(formData.entries());
      payload.sample_size = Number(payload.sample_size);
      payload.seed = payload.seed ? Number(payload.seed) : null;
      const response = await opFetchJson("/api/v1/custom-datasets/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await loadDataset(response.dataset.id);
    } catch (error) {
      status.textContent = "演示数据生成失败";
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
    manualRowForm.reset();
  });

  manualDatasetForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (state.manualRows.length < 3) {
      status.textContent = "至少需要 3 行手工样本";
      return;
    }
    status.textContent = "正在生成手工数据集";
    try {
      const formValues = Object.fromEntries(new FormData(manualDatasetForm).entries());
      const response = await opFetchJson("/api/v1/custom-datasets/manual", {
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
      status.textContent = "手工数据集生成失败";
      jsonCode.textContent = error.message;
    }
  });

  clearManualButton?.addEventListener("click", () => {
    state.manualRows = [];
    renderManualRows();
    status.textContent = "已清空手工样本列表";
  });

  exportButton?.addEventListener("click", () => {
    if (!state.lastReport) {
      status.textContent = "请先生成一个报告";
      return;
    }
    const fileName = `${state.lastReport.report_title || "report"}.md`.replace(/[\\/:*?"<>|]/g, "-");
    opDownloadText(fileName, state.lastReport.report_markdown);
  });

  renderManualRows();
  refreshCatalog().catch(() => {});
}

function initOperationalReports() {
  const root = document.querySelector("[data-operational-report-root]");
  if (!root) return;

  const state = {
    dataset: "current",
    audience: "manager",
    lastReport: null,
  };

  const form = root.querySelector("[data-report-form]");
  const datasetButtons = root.querySelectorAll("[data-report-dataset-button]");
  const customDatasetContainer = root.querySelector("[data-report-custom-datasets]");
  const audienceButtons = root.querySelectorAll("[data-audience]");
  const branchStatus = root.querySelector("[data-report-branch-status]");
  const riskLevel = root.querySelector("[data-report-risk-level]");
  const highRisk = root.querySelector("[data-report-high-risk]");
  const meanScore = root.querySelector("[data-report-mean-score]");
  const capacityWeeks = root.querySelector("[data-report-capacity-weeks]");
  const headline = root.querySelector("[data-report-headline]");
  const focus = root.querySelector("[data-report-focus]");
  const quality = root.querySelector("[data-report-quality]");
  const findings = root.querySelector("[data-report-findings]");
  const actions = root.querySelector("[data-report-actions]");
  const cohorts = root.querySelector("[data-report-cohorts]");
  const markdown = root.querySelector("[data-report-markdown] code");
  const endpoint = root.querySelector("[data-report-endpoint]");
  const jsonCode = root.querySelector("[data-report-json] code");
  const downloadButton = root.querySelector("[data-report-download]");

  function renderCustomDatasetButtons(catalog) {
    const datasets = catalog?.datasets || [];
    if (!datasets.length) {
      customDatasetContainer.innerHTML =
        '<span class="status-dot muted-status">工作台里导入的数据集会显示在这里</span>';
      return;
    }
    customDatasetContainer.innerHTML = datasets
      .map(
        (item) => `
          <button class="endpoint-pick ${item.id === state.dataset ? "is-active" : ""}" type="button" data-report-custom-dataset="${opEscapeHtml(item.id)}">
            ${opEscapeHtml(item.label)} · ${opEscapeHtml(item.scale)}
          </button>
        `
      )
      .join("");
    customDatasetContainer.querySelectorAll("[data-report-custom-dataset]").forEach((button) => {
      button.addEventListener("click", async () => {
        state.dataset = button.dataset.reportCustomDataset;
        try {
          await loadReport();
        } catch (error) {
          jsonCode.textContent = error.message;
        }
      });
    });
  }

  async function refreshCustomCatalog() {
    const catalog = await fetchCustomDatasetCatalog();
    renderCustomDatasetButtons(catalog);
    return catalog;
  }

  async function handleMissingReportDataset(datasetId) {
    state.dataset = "current";
    const catalog = await refreshCustomCatalog();
    branchStatus.textContent = `临时数据集 ${datasetId} 已失效，已回退到北美 NHANES 分支`;
    return catalog;
  }

  async function loadReport() {
    const catalog = await refreshCustomCatalog();
    if (isCustomDatasetId(state.dataset) && !customDatasetExists(catalog, state.dataset)) {
      await handleMissingReportDataset(state.dataset);
    }

    const values = Object.fromEntries(new FormData(form).entries());
    const meta = opDatasetMeta(state.dataset);
    branchStatus.textContent = meta.status;
    const url = opBuildUrl("/api/v1/institution-report", {
      dataset: state.dataset,
      audience: state.audience,
      organization_name: values.organization_name,
      report_title: values.report_title,
      threshold: values.threshold,
      weekly_capacity: values.weekly_capacity,
    });
    let data;
    try {
      data = await opFetchJson(url);
    } catch (error) {
      if (isCustomDatasetId(state.dataset) && isMissingCustomDatasetError(error)) {
        await handleMissingReportDataset(state.dataset);
        return loadReport();
      }
      throw error;
    }
    state.lastReport = data;
    riskLevel.textContent = opFormatValue(data.risk_level.label);
    highRisk.textContent = opFormatValue(data.risk_level.high_risk_rate_pct, "%");
    meanScore.textContent = opFormatValue(data.risk_level.mean_score);
    capacityWeeks.textContent = opFormatValue(data.capacity_plan.estimated_counselor_weeks);
    headline.textContent = data.audience_headline || data.report_title;
    focus.innerHTML = data.executive_summary.map((item) => `<li>${opEscapeHtml(item)}</li>`).join("");
    quality.innerHTML = data.data_quality.checks.map(opCreateQualityCard).join("");
    findings.innerHTML = data.key_findings.map(opCreateInsightCard).join("");
    actions.innerHTML = data.priority_actions.map(opCreateInsightCard).join("");
    cohorts.innerHTML = data.priority_cohorts.map(opCreateCohortCard).join("");
    markdown.textContent = data.report_markdown;
    endpoint.textContent = url;
    jsonCode.textContent = opPrettyJson(data);

    // 同步打印详细数据
    const cap = data.capacity_plan_detail || data.capacity_plan || {};
    root.querySelector("[data-print-threshold]")?.setAttribute("data-print-threshold", String(cap.threshold || data.capacity_plan?.threshold || ""));
    const thresholdEls = root.querySelectorAll("[data-print-threshold]");
    thresholdEls.forEach(el => { el.textContent = String(cap.threshold || data.capacity_plan?.threshold || ""); });

    const flaggedNEls = root.querySelectorAll("[data-print-flagged-n]");
    flaggedNEls.forEach(el => { el.textContent = String(cap.flagged_n ?? data.capacity_plan?.flagged_n ?? "-"); });

    const flaggedPctEls = root.querySelectorAll("[data-print-flagged-pct]");
    flaggedPctEls.forEach(el => { el.textContent = String(cap.weighted_pct ?? data.capacity_plan?.flagged_weighted_pct ?? "-"); });

    const meanScoreEls = root.querySelectorAll("[data-print-mean-score]");
    meanScoreEls.forEach(el => { el.textContent = String(cap.mean_score ?? data.capacity_plan?.mean_flagged_mental_health_score ?? "-"); });

    const defaultThEls = root.querySelectorAll("[data-print-default-threshold]");
    defaultThEls.forEach(el => { el.textContent = String(data.capacity_plan?.default_threshold ?? "-"); });

    const deltaNEls = root.querySelectorAll("[data-print-delta-n]");
    deltaNEls.forEach(el => { el.textContent = String(cap.delta_vs_baseline_n ?? data.capacity_plan?.delta_vs_default_threshold_n ?? "-"); });

    const deltaPctEls = root.querySelectorAll("[data-print-delta-pct]");
    deltaPctEls.forEach(el => { el.textContent = String(cap.delta_vs_baseline_pct ?? data.capacity_plan?.delta_vs_threshold_10_pct_point ?? "-"); });

    const recEls = root.querySelectorAll("[data-print-recommendation]");
    recEls.forEach(el => { el.textContent = String(cap.recommendation ?? data.capacity_plan?.recommended_use ?? "-"); });

    const riskFactorsBody = root.querySelector("[data-print-risk-factors-body]");
    if (riskFactorsBody && data.key_risk_factors) {
      riskFactorsBody.innerHTML = data.key_risk_factors
        .map(
          (row, i) =>
            `<tr><td>${i + 1}</td><td>${opEscapeHtml(row.dimension)} / ${opEscapeHtml(row.group)}</td><td>${opFormatValue(row.participants)} 人</td><td>${opFormatValue(row.high_risk_rate_pct, "%")}</td><td>+${opFormatValue(row.uplift_vs_overall_pct_point, " pt")}</td></tr>`
        )
        .join("");
    }

    const comparisonBody = root.querySelector("[data-print-comparison-body]");
    if (comparisonBody && data.comparison_highlights) {
      comparisonBody.innerHTML = data.comparison_highlights
        .map(
          (row) =>
            `<tr><td>${opEscapeHtml(row.group || "-")}</td><td>${opFormatValue(row.current_high_risk_rate_pct, "%")}</td><td>${opFormatValue(row.legacy_high_risk_rate_pct, "%")}</td><td>${opFormatValue(row.change_pct_point, " pt")}</td></tr>`
        )
        .join("");
    }

    const cohortsBody = root.querySelector("[data-print-cohorts-body]");
    if (cohortsBody && data.priority_cohorts) {
      cohortsBody.innerHTML = data.priority_cohorts
        .map(
          (row, i) =>
            `<tr><td>${i + 1}</td><td>${opEscapeHtml(row.segment_label || "-")}</td><td>${opFormatValue(row.participants)} 人</td><td>${opFormatValue(row.high_risk_rate_pct, "%")}</td><td>${opFormatValue(row.mean_mental_health_score)}</td><td>+${opFormatValue(row.uplift_vs_overall_pct_point, " pt")}</td></tr>`
        )
        .join("");
    }
    opSetButtonState(datasetButtons, state.dataset, (button) => button.dataset.reportDatasetButton);
    opSetButtonState(audienceButtons, state.audience, (button) => button.dataset.audience);
    await refreshCustomCatalog();
  }

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

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await loadReport();
    } catch (error) {
      jsonCode.textContent = error.message;
    }
  });

  downloadButton?.addEventListener("click", () => {
    if (!state.lastReport) {
      return;
    }
    const fileName = `${state.lastReport.report_title || "institution-report"}.md`.replace(/[\\/:*?"<>|]/g, "-");
    opDownloadText(fileName, state.lastReport.report_markdown);
  });

  loadReport().catch(() => {});
}

document.addEventListener("DOMContentLoaded", () => {
  initOperationalWorkbench();
  initOperationalReports();
});

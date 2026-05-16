const prettyJson = (data) => JSON.stringify(data, null, 2);

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`);
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

function createBarRow(row) {
  const group = row.group || `${row.age_band} / ${row.gender} / ${row.income_band}`;
  const rate = row.elevated_priority_rate_pct ?? 0;
  return `
    <div class="bar-item">
      <div class="bar-label">
        <span>${group}</span>
        <strong>${rate}%</strong>
      </div>
      <div class="bar-track">
        <div class="bar-fill" style="width:${Math.max(0, Math.min(100, rate))}%"></div>
      </div>
    </div>
  `;
}

function createCohortCard(row) {
  return `
    <article class="cohort-card">
      <div class="cohort-title">${row.age_band} / ${row.gender} / ${row.income_band}</div>
      <div class="cohort-meta">${row.participants} 人样本</div>
      <div class="metric-inline">
        <span>短睡眠</span>
        <strong>${row.short_sleep_rate_pct}%</strong>
      </div>
      <div class="metric-inline">
        <span>高优先级</span>
        <strong>${row.elevated_priority_rate_pct}%</strong>
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
    const data = await fetchJson(`/api/v1/population-profile?group_by=${group}&min_participants=80`);
    const topRows = data.rows.slice(0, 5);
    bars.innerHTML = topRows.map(createBarRow).join("");
    jsonEl.textContent = prettyJson(data);
    root.dataset.currentGroup = group;
    buttons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.homeGroup === group);
    });
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

  const form = root.querySelector("[data-profile-form]");
  const bars = root.querySelector("[data-profile-bars]");
  const status = root.querySelector("[data-profile-status]");
  const jsonCode = root.querySelector("[data-live-json] code");
  const endpointLabel = root.querySelector("[data-endpoint-label]");
  const endpointButtons = root.querySelectorAll("[data-endpoint-target]");
  const cohortBoard = root.querySelector("[data-cohort-board]");

  const summaryShort = root.querySelector("[data-summary-short-sleep]");
  const summarySedentary = root.querySelector("[data-summary-sedentary]");
  const summaryElevated = root.querySelector("[data-summary-elevated]");
  const summaryRows = root.querySelector("[data-summary-rows]");

  async function refreshSummary() {
    const data = await fetchJson("/api/v1/summary");
    summaryShort.textContent = `${data.behavioral_signals.short_sleep_rate_pct}%`;
    summarySedentary.textContent = `${data.behavioral_signals.high_sedentary_rate_pct}%`;
    summaryElevated.textContent = `${data.behavioral_signals.elevated_rate_pct}%`;
    summaryRows.textContent = `${data.sample.merged_adult_rows}`;
  }

  async function refreshProfile(formData) {
    const query = new URLSearchParams(formData).toString();
    const endpoint = `/api/v1/population-profile?${query}`;
    status.textContent = "加载中";
    endpointLabel.textContent = endpoint;
    const data = await fetchJson(endpoint);
    bars.innerHTML = data.rows.slice(0, 8).map(createBarRow).join("");
    jsonCode.textContent = prettyJson(data);
    status.textContent = "已更新";
    endpointButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.endpointTarget === endpoint);
    });
  }

  async function refreshCohorts() {
    const data = await fetchJson("/api/v1/priority-cohorts?limit=6&min_participants=100");
    cohortBoard.innerHTML = data.rows.map(createCohortCard).join("");
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
      endpointButtons.forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
      const target = button.dataset.endpointTarget;
      endpointLabel.textContent = target;
      try {
        const data = await fetchJson(target);
        jsonCode.textContent = prettyJson(data);
      } catch (error) {
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

  Promise.all([refreshSummary(), refreshCohorts()]).catch(() => {});
}

function initReports() {
  const root = document.querySelector("[data-report-root]");
  if (!root) return;
  const buttons = root.querySelectorAll("[data-audience]");
  const headline = root.querySelector("[data-report-headline]");
  const focus = root.querySelector("[data-report-focus]");
  const notes = root.querySelector("[data-report-notes]");
  const cohorts = root.querySelector("[data-report-cohorts]");
  const endpoint = root.querySelector("[data-report-endpoint]");
  const jsonCode = root.querySelector("[data-report-json] code");

  async function loadReport(audience) {
    const url = `/api/v1/reports/${audience}`;
    const data = await fetchJson(url);
    headline.textContent = data.headline;
    focus.innerHTML = data.focus_points.map((item) => `<li>${item}</li>`).join("");
    notes.innerHTML = data.shared_notes.map((item) => `<li>${item}</li>`).join("");
    cohorts.innerHTML = data.top_cohorts.map(createCohortCard).join("");
    endpoint.textContent = url;
    jsonCode.textContent = prettyJson(data);
    buttons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.audience === audience);
    });
  }

  buttons.forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await loadReport(button.dataset.audience);
      } catch (error) {
        jsonCode.textContent = error.message;
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initMobileNav();
  initReveal();
  initHomeProfileSwitcher();
  initStudio();
  initReports();
});

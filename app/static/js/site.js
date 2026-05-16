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

function initExamples() {
  const root = document.querySelector("[data-example-root]");
  if (!root) return;

  const examples = {
    community: {
      badge: "机构运营场景",
      title: "市级心理健康中心如何识别优先筛查人群",
      summary:
        "团队需要在有限预算下安排下一轮筛查与外展服务，希望先看清哪些群体同时呈现短睡眠、久坐和低收入信号。",
      tags: ["重点人群识别", "筛查优先级排序", "管理汇报摘要"],
      steps: [
        ["读取样本", "先从人口学、睡眠和活动数据里建立分析基础。"],
        ["识别重点群体", "按年龄、收入和行为信号定位优先筛查对象。"],
        ["生成机构简报", "把结果整理成管理团队能快速理解的语言。"],
      ],
      outcomeTitle: "一份可直接进入周会讨论的优先级名单",
      outcomes: [
        "优先筛查群体组合列表",
        "重点信号占比与说明",
        "适合管理层阅读的摘要语言",
      ],
      endpoints: ["/api/v1/priority-cohorts", "/api/v1/reports/manager"],
    },
    campus: {
      badge: "学生服务场景",
      title: "高校学生支持中心如何提前发现高压力生活方式人群",
      summary:
        "学校希望在学期中段提前锁定睡眠不足、活动下降、需要重点触达的学生群体，用于安排宣传、筛查与支持服务。",
      tags: ["学生支持", "学期筛查计划", "触达策略优化"],
      steps: [
        ["分层查看画像", "先看不同年龄段与群体的行为模式差异。"],
        ["圈定重点对象", "识别高优先级占比更高的学生人群组合。"],
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
        "医院管理部门希望用更短时间理解高负担群体组合，把服务量能、宣教资源和筛查安排投向更需要的对象。",
      tags: ["资源配置", "运营汇报", "服务优先级"],
      steps: [
        ["汇总总体信号", "先确认短睡眠、久坐和高优先级占比等全局指标。"],
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
  initExamples();
  initVisionMap();
});

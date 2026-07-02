# HealthInsight 产品重新设计工作记录

> 最后更新：2026-07-01 14:28

---

## 一、已完成的工作

### 1. 制定了重新设计方案
**文件：** `REDESIGN_PLAN.md`

核心思路：
- **问题诊断**：产品定位不清，用户找不到入口，一直在做功能展示而非帮助用户完成任务
- **重新定位**：HealthInsight 是一个"心理健康风险识别工作台"，不是仪表盘展示站
- **三步操作流**：导入数据 → 一键分析 → 生成报告
- **新导航结构**：精简为 3 大区块（首页、工作台、报告中心）

### 2. 精简了导航结构
**文件：** `app/main.py`

- 删除了原来的三层嵌套下拉菜单（产品概览 / 分析工作台 / 说明与扩展）
- 改为简洁的三个一级导航项：首页、工作台、报告中心
- 新增"API 文档"作为辅助入口
- 简化了 `page_context` 函数

### 3. 更新了 base.html
**文件：** `app/templates/base.html`

- 导航改为平铺式，不再有下拉菜单
- 更新了 brand-mark 文字（从"机构级健康洞察平台"改为"心理健康风险识别工作台"）
- 更新了 footer，添加了底部导航链接

### 4. 精简了报告内容
**文件：** `app/analytics.py`

这是改动最大的部分。分 4 个脚本完成：

#### part 1 - base_summary + researcher
- `base_summary`：从冗长句式精简为两行核心数据
- researcher `executive_summary` 和 `priority_actions`：精简了 3 个 action 的 title、owner、detail、timeline

#### part 2 - clinical + engineering + manager
- clinical：精简为 3 行核心 action
- engineering：精简为 3 行核心 action
- manager：精简为 3 行核心 action
- 所有 audience_notes 精简为一行

#### part 3 - key_findings + notes
- `key_findings` 中的所有 detail 文字精简
- `notes` 从 3 行合并精简为 3 行核心说明
- 删除了受众视角（audience_snapshot["focus_points"]）的重复展示

#### part 4 - Markdown 报告格式
- 重新设计了 Markdown 报告的输出格式
- 报告头信息整合为两行（一行机构信息，一行风险数据）
- 关键发现用粗体标题 + 详情格式
- 优先行动用粗体格式：标题 + 负责人 + 时间 + 详情
- 数据质量状态用中文括号
- 末尾添加了分隔线和生成时间

---

## 二、未完成的工作

### 必须完成
- [ ] **前端模板重构**（最高优先级）
  - [ ] `app/templates/index.html` - 新首页设计（目前还是旧版）

### 可选完成
- [ ] 更新 README.md，反映新的产品定位
- [ ] 删除不再使用的模板文件：`scenarios.html`, `examples.html`, `workbench.html`, `reports.html`
- [ ] 删除临时 Python 脚本（`fix_analytics*.py`）

---

## 三、报告内容改进总结

### 改进前 vs 改进后

| 位置 | 改进前（问题） | 改进后 |
|------|--------------|--------|
| base_summary | 冗长的两段话 | 两行核心数据（样本量、完整率、风险率、平均分） |
| executive_summary | "建议把阈值...命中的...人作为首轮复核池，并优先联系..." | "阈值10命中240人，建议优先联系xxx" |
| priority_actions | "先形成首批筛查名单" + "围绕高风险组合配置资源" + "补齐关键字段质量" | 精简为 action 名 + 一句话详情 |
| key_findings | "重点人群已明确" + 长段说明 | "重点人群已明确" + 一行核心数据 |
| notes | 3-5行说明 | 3行核心声明 |
| Markdown 格式 | 繁杂的元信息 + 无格式列表 | 紧凑表头 + 粗体标题 + 结构化内容 |

---

## 四、下一步操作建议

### 第一步：验证报告效果
```powershell
.\start.ps1
```
然后访问 `http://127.0.0.1:8000/api/v1/reports/manager`，查看 JSON 返回的 `report_markdown` 字段，确认报告内容已精简。

### 第二步：重构首页
按照 `REDESIGN_PLAN.md` 第四节的指引，重写 `index.html`：
- 删除所有 API 预览、JSON 输出
- 保留：三步操作流程、典型场景卡片、平台数据总览
- 添加：直接进入工作台的 CTA

### 第三步：简化报告页面
修改 `reports_real.html`，参考以下原则：
- 隐藏技术细节（JSON 预览折叠或删除）
- 突出报告预览区域
- 简化控制台选项

### 第四步：更新 CSS
运行 `.\start.ps1` 后检查现有样式是否有破坏，然后逐步完善。

---

## 五、关键文件清单

| 文件 | 状态 | 说明 |
|------|------|------|
| `REDESIGN_PLAN.md` | ✅ 完成 | 完整设计方案 |
| `app/main.py` | ✅ 完成 | 导航结构 + 路由简化 |
| `app/templates/base.html` | ✅ 完成 | 新导航 + 新 footer |
| `app/analytics.py` | ✅ 完成 | 报告内容全面精简 + 新增打印数据字段 |
| `app/static/css/operational.css` | ✅ 完成 | `@media print` 样式 |
| `app/static/js/operational.js` | ✅ 完成 | 打印数据同步逻辑 |
| `app/templates/index.html` | ❌ 未完成 | 待重构 |
| `app/templates/workbench_real.html` | ❌ 未完成 | 待重构 |
| `app/templates/reports_real.html` | ✅ 完成 | 新增打印区块 |
| `app/static/css/site.css` | ✅ 完成 | `@media print` 样式 |
| `app/static/js/operational.js` | ✅ 完成 | 打印数据同步 |

---

## 七、打印功能（网页简略版 + 打印详细版）

**完成时间：2026-07-02**

### 设计思路
- **网页版**：保持简洁，只显示核心指标和行动建议
- **打印版**：追加详细数据表（阈值模拟、风险因子排名、年龄段对照、重点人群完整数据），网页隐藏，打印时显示

### 打印详细版包含的内容
1. **阈值模拟详情**：命中人数、加权占比、高风险人群平均分、相比默认值的变化、建议用途
2. **风险因子排名 Top 5**：维度/分层、样本量、高风险率、高于总体百分点
3. **年龄段对照**：当前 vs 参考分支的高风险率变化
4. **重点人群完整数据 Top 5**：人群标签、样本量、高风险率、平均分、高于总体百分点

### 关键文件改动
| 文件 | 改动 |
|------|------|
| `app/analytics.py` | 返回值新增 `capacity_plan_detail` 字段（结构化后的阈值模拟详情） |
| `app/templates/reports_real.html` | 新增打印区块；Hero 区添加"打印报告"和"导出 PDF"按钮（均调用 `window.print()`） |
| `app/static/css/operational.css` | 新增 `.print-only` 隐藏类；`@media print` 中隐藏控制台、按钮等网页元素，显示详细区块；`@page` 设置边距 |
| `app/static/js/operational.js` | `loadReport()` 中新增数据同步逻辑，将 API 数据注入打印区块的 DOM 元素 |

### 打印按钮说明
- "打印报告"和"导出 PDF"两个按钮实际上都调用 `window.print()`，用户选择"另存为 PDF"即可
- 不在后端生成 PDF，避免 `wkhtmltopdf` 依赖和额外复杂度

### 验证方法
1. 启动服务后访问 `http://127.0.0.1:8000/reports`
2. 点击浏览器打印预览（或 Ctrl+P），确认详细数据表在打印输出中出现
3. 切换受众/数据集后再次打印，确认数据同步更新

```powershell
# 启动服务
.\start.ps1

# 验证报告 API
curl http://127.0.0.1:8000/api/v1/institution-report?audience=manager

# 验证首页
start http://127.0.0.1:8000/

# 验证报告页
start http://127.0.0.1:8000/reports
```

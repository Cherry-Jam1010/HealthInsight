# HealthInsight

HealthInsight 是一个面向公共卫生、心理健康机构、医院管理团队与研究团队的双数据源心理健康洞察平台。项目同时提供：

- 基于 `FastAPI` 的版本化 API
- 面向非技术用户的多页面产品展示站
- 面向技术团队的交互式接口文档

当前版本围绕 `PHQ-9` 风险识别、重点人群发现、双周期对照与阈值模拟展开，定位为**机构级筛查支持与决策辅助工具**，不用于个人临床诊断。

## 核心能力

- `PHQ-9` 总分计算与高风险标签构建
- 年龄、性别、收入、教育、睡眠、BMI、慢病负担等分层画像
- 重点筛查人群组合识别
- 当前风险与历史行为基线对照
- 阈值模拟与初步资源承接估算
- 面向研究、管理、临床、技术团队的角色化简报

## 数据来源

项目当前使用两套数据：

### 1. 当前周期心理健康主分析数据

目录：`NHANES/`

- `DEMO_L.xpt`：人口学与样本权重
- `DPQ_L.xpt`：`PHQ-9` 抑郁筛查问卷
- `SLQ_L.xpt`：睡眠时长
- `BMX_L.xpt`：BMI 与身体测量
- `MCQ_L.xpt`：慢病与医疗状况

### 2. 历史行为基线数据

目录：`data/`

- `P_DEMO.xpt`：历史人口学基线
- `P_SLQ.xpt`：历史睡眠基线
- `P_PAQ.xpt`：历史活动基线

当前周期负责识别心理健康风险，历史周期负责补充睡眠和活动背景，两者共同构成平台的双数据源分析框架。

## 当前接口

- `GET /api/v1/health`
- `GET /api/v1/capabilities`
- `GET /api/v1/datasets`
- `GET /api/v1/summary`
- `GET /api/v1/population-profile?group_by=age_band`
- `GET /api/v1/priority-cohorts`
- `GET /api/v1/risk-patterns`
- `GET /api/v1/risk-factors`
- `GET /api/v1/cycle-comparison?group_by=age_band`
- `GET /api/v1/threshold-simulate?threshold=10&weekly_capacity=20`
- `GET /api/v1/reports/{audience}`

## 前端页面

- `/`         首页
- `/workbench` 工作台（数据导入 + 实时分析）
- `/reports`  报告中心（生成和下载正式报告）
- `/guide`    使用指南
- `/vision`   全球视野
- `/docs`     交互式 API 文档

**产品路径**：首页 → 工作台（导入数据 / 生成分析）→ 报告中心（生成报告 / 下载）

## 本地运行

推荐优先使用仓库自带虚拟环境。

稳定启动：

```powershell
.\start.ps1
```

开发模式：

```powershell
.\start-dev.ps1
```

指定端口：

```powershell
.\start.ps1 -Port 8010
```

也可以直接运行：

```powershell
.\.healthee\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

启动后可访问：

- `http://127.0.0.1:8000/`         首页
- `http://127.0.0.1:8000/workbench` 工作台
- `http://127.0.0.1:8000/reports`   报告中心
- `http://127.0.0.1:8000/guide`     使用指南
- `http://127.0.0.1:8000/docs`      API 文档

## 文档与下载

仓库内已提供以下文档：

- [API_STRATEGY.md](./API_STRATEGY.md)：API 架构说明
- [FRAME.md](./FRAME.md)：产品定位与原始设计框架
- [docs/HealthInsight_API_Quickstart_CN.md](./docs/HealthInsight_API_Quickstart_CN.md)：快速开始

站点内也提供下载入口：

- `/downloads/quickstart`
- `/downloads/api-strategy`
- `/downloads/readme`
- `/downloads/openapi`

## Cloudflare Tunnel 临时分享

项目包含 `share.ps1`，可用于将本地服务临时公开分享。

前提：

- 本地已安装或下载 `cloudflared.exe`
- `cloudflared.exe` 位于项目根目录，或已加入系统环境变量

启动分享：

```powershell
.\share.ps1
```

指定 `cloudflared.exe` 路径：

```powershell
.\share.ps1 -CloudflaredPath "C:\path\to\cloudflared.exe"
```

脚本会：

- 启动本地 `FastAPI` 服务
- 建立 `Cloudflare Quick Tunnel`
- 输出一个新的 `trycloudflare.com` 公网地址

注意：

- 每次重新运行 `share.ps1` 都会生成新的外网链接
- 旧的 `trycloudflare.com` 链接会失效
- 该方式适合演示与临时分享，不适合长期正式部署

## Hugging Face Spaces 部署

仓库已包含 Hugging Face Docker Space 所需文件：

- `Dockerfile`
- `HF_SPACE_README.md`
- `.github/workflows/sync-to-hf-space.yml`

当前部署方式为：

1. 代码推送到 GitHub `main`
2. GitHub Actions 自动同步到 Hugging Face Space
3. Hugging Face 按 Docker Space 方式构建并运行

### Hugging Face 相关约束

- `HF_SPACE_README.md` 会在同步时复制为 Space 使用的 `README.md`
- 工作流会排除 `.git`、`.github`、`data/*.xpt`、`NHANES/*.xpt`
- 大型二进制数据文件不会直接推送到 Hugging Face Space

### 当前运行环境

- Python `3.11`
- `fastapi==0.136.1`
- `uvicorn[standard]==0.47.0`
- `pandas==3.0.3`
- `jinja2==3.1.6`
- `numpy==2.4.4`

## 项目结构

```text
app/
  analytics.py           # 双数据源读取、清洗、合并、特征衍生与统计
  main.py                # FastAPI 应用与网页路由
  templates/             # 网站模板
  static/                # CSS、JS 与图标资源
docs/
  HealthInsight_API_Quickstart_CN.md
data/                    # 历史行为基线数据
NHANES/                  # 当前周期心理健康分析数据
API_STRATEGY.md
FRAME.md
HF_SPACE_README.md
Dockerfile
share.ps1
```

## 使用边界

- 平台输出的是群体层面的风险洞察与筛查支持信息
- `PHQ-9` 高风险标签表示筛查阳性风险，不等同于临床确诊
- 结果适用于研究分析、项目规划、机构汇报与资源配置支持
- 平台不替代医生、心理咨询师或正式临床评估流程

## 后续方向

- 接入更多医疗可及性、保险与服务利用变量
- 增加独立预测模型、公平性检查与阈值优化
- 增加上传分析、异步任务与报告导出
- 扩展到更多地区、多语言与跨机构对照场景

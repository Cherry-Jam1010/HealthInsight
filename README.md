# HealthInsight API MVP

## 项目简介

这个仓库现在已经被整理成一套可运行的中文产品原型，包含两部分：

- 一个基于 `FastAPI` 的版本化健康洞察 API
- 一个面向机构用户的前端展示站，用来直观展示 API 能力

它不是单纯的“课程脚本集合”，而是朝着真正产品化形态推进的一版 MVP。

## 当前数据能做什么

`data/` 目录当前包含：

- `P_DEMO.xpt`：人口学与访谈权重
- `P_PAQ.xpt`：体力活动
- `P_SLQ.xpt`：睡眠

基于这三份数据，当前版本支持：

- 数据体检与覆盖率展示
- 年龄 / 性别 / 收入 / 族裔分层画像
- 睡眠与活动行为负担摘要
- 机构级“优先关注群体”识别
- 面向研究者、管理者、临床团队、工程团队的角色化摘要

当前版本还**不支持**：

- PHQ-9 抑郁风险预测
- 基于真实标签的公平性评估
- 贝叶斯阈值推荐

如果你要进入你在 `FRAME.md` 里写的“心理健康风险分析主线”，下一步最关键的是补充 `P_DPQ.xpt`。

## 本地运行

建议优先使用仓库自带虚拟环境，不要直接用系统 Python。

稳定启动：

```powershell
.\start.ps1
```

开发模式启动：

```powershell
.\start-dev.ps1
```

如果 `8000` 端口被占用，可以直接换端口：

```powershell
.\start.ps1 -Port 8010
```

```powershell
.\start-dev.ps1 -Port 8010
```

如果你想手动运行，也建议使用下面这两个命令：

稳定模式：

```powershell
.\.healthee\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

开发模式：

```powershell
.\.healthee\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

说明：

- Windows 下 `--reload` 会额外拉起子进程。
- 如果你在子进程刚启动时中断，可能会看到 `SpawnProcess-1` 和 `KeyboardInterrupt`。
- 这通常不是项目代码错误，而是热重载子进程在退出时被打断。
- 如果只是想稳定打开站点，优先用 `.\start.ps1`。

启动后访问：

- `http://127.0.0.1:8000/`：产品首页
- `http://127.0.0.1:8000/scenarios`：应用场景页
- `http://127.0.0.1:8000/studio`：API 展示台
- `http://127.0.0.1:8000/reports`：报告中心
- `http://127.0.0.1:8000/docs`：交互式接口文档

## 主要接口

- `GET /api/v1/health`
- `GET /api/v1/capabilities`
- `GET /api/v1/datasets`
- `GET /api/v1/summary`
- `GET /api/v1/population-profile?group_by=age_band`
- `GET /api/v1/priority-cohorts`
- `GET /api/v1/reports/{audience}`

## 前端页面说明

当前站点已经不是单页，而是多页面产品展示结构：

- 首页：突出产品定位、核心能力和动态数据展示
- 应用场景页：讲清不同机构用户为什么需要它
- API 展示台：实时调用接口并展示返回结果
- 报告中心：切换不同角色的摘要输出

## 项目结构

```text
app/
  analytics.py           # NHANES 读取、清洗、合并、特征衍生与统计
  main.py                # FastAPI 应用与网站路由
  templates/
    base.html            # 中文站点底座模板
    index.html           # 首页
    scenarios.html       # 应用场景页
    studio.html          # API 展示台
    reports.html         # 报告中心
  static/
    css/site.css         # 站点视觉样式
    js/site.js           # 前端交互逻辑
API_STRATEGY.md          # API 架构说明
FRAME.md                 # 原始产品定位文档
data/                    # NHANES 数据
```

## 推荐下一步

如果要继续做成更完整的课程项目或可演示作品，建议按这个顺序推进：

1. 接入 `P_DPQ.xpt`，把 PHQ-9 相关能力做成真实模块。
2. 补 BMI、慢病、医疗可及性等变量，支撑更完整的解释层。
3. 新增公平性审计与阈值推荐接口。
4. 增加上传用户数据、异步分析任务与 PDF 报告导出。

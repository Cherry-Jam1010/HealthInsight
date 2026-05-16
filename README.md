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

## 部署到 Render

仓库已经包含 `render.yaml`，可以直接按 Render 的 Web Service / Blueprint 流程部署。

关键信息：

- Build Command: `pip install -r requirements.txt`
- Start Command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check: `/api/v1/health`

如果你只是想最快把网站分享出去，推荐先部署到 Render。

## 部署到 Koyeb

如果你不想用 Render，也暂时不想继续卡在 Hugging Face，`Koyeb` 是当前最适合这个项目的备选方案。它支持直接从 GitHub 拉取仓库，也支持按仓库中的 `Dockerfile` 自动构建。

当前仓库已经具备 Koyeb 所需的基础条件：

- 有可直接启动的 `Dockerfile`
- 应用支持读取平台注入的 `PORT`
- 首页、静态资源和 API 都由同一个 FastAPI 服务提供

### 第一步：注册并登录 Koyeb

打开：

```text
https://app.koyeb.com/
```

注册后进入控制台。

### 第二步：创建 Web Service

在控制台中点击：

- `Create Web Service`

部署方式选择：

- `GitHub`

然后连接你的 GitHub 账号，并选择仓库：

```text
Cherry-Jam1010/HealthInsight
```

分支选择：

```text
main
```

### 第三步：选择 Dockerfile 构建

因为仓库根目录已经有 `Dockerfile`，Koyeb 会自动识别并按 Dockerfile 构建。

如果页面里允许你手动选择构建方式，优先选：

- `Dockerfile`

### 第四步：检查运行参数

这个项目当前容器启动命令已经写在 `Dockerfile` 里，一般不需要手改。Koyeb 会自动注入 `PORT` 环境变量，应用会监听这个端口。

如需手动确认，核心启动逻辑是：

```text
python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
```

### 第五步：公开服务端口

创建服务时，确认它是一个公开的 Web Service，并把 HTTP 路由指向应用监听端口。

如果页面需要你手填端口，填：

```text
7860
```

如果 Koyeb 自动根据 `PORT` 识别端口，保持默认即可。

### 第六步：选择实例规格

如果你账号里可以选免费实例，优先选择：

- `Free`

如果界面没有免费规格，就按你账号当前能用的最低规格选择。

### 第七步：等待构建和启动

创建后，Koyeb 会自动：

- 拉取 GitHub 仓库
- 根据 `Dockerfile` 构建镜像
- 启动 Web Service

启动成功后，你会拿到一个类似下面的公开地址：

```text
https://xxx.koyeb.app
```

### 第八步：上线后检查

建议至少检查这些页面：

- `/`
- `/scenarios`
- `/studio`
- `/reports`
- `/docs`
- `/api/v1/health`

例如：

```text
https://你的域名.koyeb.app/
https://你的域名.koyeb.app/docs
https://你的域名.koyeb.app/api/v1/health
```

### 注意事项

- 当前仓库默认会把 `data/` 中的 NHANES 数据一并打包进镜像，所以 Koyeb 上不需要额外下载数据。
- 如果后面你想减小镜像体积，也可以像 Hugging Face 方案那样改成运行时下载数据。
- 如果部署成功但页面打不开，优先检查 Koyeb 中 Web Service 的公开端口配置和运行日志。

## 部署到 Hugging Face Spaces

如果你还是想用 Hugging Face，这个仓库已经准备好了 Docker Space 所需文件：

- `Dockerfile`
- `HF_SPACE_README.md`
- `.github/workflows/sync-to-hf-space.yml`

这套方案不要求你在本机直接 `git push` 到 Hugging Face，而是让 GitHub Actions 自动把 `main` 分支同步到你的 Space，适合本机网络连不上 `huggingface.co` 的情况。

### 第一步：创建 Space

在 Hugging Face 网页里创建一个新的 Space：

- Space 类型选择 `Docker`
- Space 名称建议使用 `healthinsight`
- 可见性先选 `Public`

如果你后面想对外公开分享网站，`Public` 最省事。

### 第二步：创建 Hugging Face Token

打开 Hugging Face 的 Token 页面，创建一个带 `write` 权限的访问令牌。这个令牌后面会配置到 GitHub 的仓库密钥里。

### 第三步：在 GitHub 配置自动同步

打开你的 GitHub 仓库：

- `Settings`
- `Secrets and variables`
- `Actions`

先添加一个 Secret：

- Name: `HF_TOKEN`
- Value: 你刚刚创建的 Hugging Face write token

再添加一个 Variable：

- Name: `HF_SPACE_ID`
- Value: `你的 Hugging Face 用户名/healthinsight`

例如：

```text
Cherry1010/healthinsight
```

### 第四步：触发同步

只要你把代码推到 GitHub 的 `main` 分支，这个工作流就会自动运行，把当前仓库内容同步到你的 Hugging Face Space。

你也可以在 GitHub 的 `Actions` 页面里手动运行：

- `Sync to Hugging Face Space`
- `Run workflow`

### 第五步：等待 Space 构建

同步完成后，Hugging Face 会自动开始构建 Docker Space。构建成功后，你就可以通过下面这个地址访问网站：

```text
https://huggingface.co/spaces/你的用户名/healthinsight
```

通常也会有一个直接访问应用的子域名：

```text
https://你的用户名-healthinsight.hf.space
```

### 注意事项

- 这个工作流会先把 `HF_SPACE_README.md` 复制成 Space 需要的 `README.md`，再推送到 Hugging Face。
- 工作流会在 GitHub Runner 中生成一个临时同步目录，并自动排除 `.github/` 和 `.git/` 目录。
- 为了避开 Hugging Face 对二进制数据文件的推送限制，工作流不会把 `data/*.xpt` 同步到 Space；应用会在 Hugging Face 启动时自动从 GitHub 原仓库下载这些文件。
- 如果仓库里将来出现超过 `10MB` 的大文件，按 Hugging Face 官方说明，需要改用 Git LFS。

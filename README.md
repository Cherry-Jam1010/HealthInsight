# HealthInsight API MVP

## 项目简介

这个仓库现在已经被整理成一套可运行的中文产品原型，包含两部分：

- 一个基于 `FastAPI` 的版本化健康洞察 API
- 一个面向机构用户的前端展示站，用来直观展示 API 能力

它不是单纯的“课程脚本集合”，而是朝着真正产品化形态推进的一版 MVP。

## 当前数据能做什么

当前版本优先使用 `NHANES/` 目录中的 **NHANES August 2021-August 2023** 公开成人数据模块：

- `DEMO_L.xpt`：人口学与样本权重
- `DPQ_L.xpt`：PHQ-9 抑郁筛查问卷
- `SLQ_L.xpt`：睡眠时长
- `BMX_L.xpt`：BMI 与身体测量
- `MCQ_L.xpt`：慢病与医疗状况

基于这五份数据，当前版本支持：

- PHQ-9 总分与高风险标签构建
- 数据体检与变量覆盖率展示
- 年龄 / 性别 / 收入 / 族裔 / 教育 / 睡眠 / BMI / 慢病负担分层画像
- 高风险组合识别
- 风险因素线索整理
- PHQ-9 阈值模拟与初步资源估算
- 面向研究者、管理者、临床团队、工程团队的角色化摘要

当前版本还**不支持**：

- 独立的抑郁风险预测模型
- 系统化公平性审计
- 基于预测概率的校准与阈值优化

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
- `GET /api/v1/risk-patterns`
- `GET /api/v1/risk-factors`
- `GET /api/v1/threshold-simulate?threshold=10&weekly_capacity=20`
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
data/                    # 旧版行为数据
NHANES/                  # 2021-2023 心理健康风险分析数据
```

## 推荐下一步

如果要继续做成更完整的课程项目或可演示作品，建议按这个顺序推进：

1. 接入更多医疗可及性、保险与服务利用变量，丰富解释层。
2. 增加独立预测模型、公平性检查和分组阈值优化。
3. 增加上传用户数据、异步分析任务与 PDF 报告导出。
4. 继续扩展全球数据源与多地区、多语言对比能力。

## 部署到 Render

仓库已经包含 `render.yaml`，可以直接按 Render 的 Web Service / Blueprint 流程部署。

关键信息：

- Build Command: `pip install -r requirements.txt`
- Start Command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check: `/api/v1/health`

如果你只是想最快把网站分享出去，推荐先部署到 Render。

## 用 Cloudflare Tunnel 分享网站

如果你现在的目标是先把网站发给老师、同学或产品用户看，`Cloudflare Tunnel` 是最省事的方式。它不需要把项目部署到新平台，只要你的本地服务能跑起来，就能立刻生成一个公网链接。

官方文档：

- `Cloudflare Tunnel`：https://developers.cloudflare.com/tunnel/
- `Quick tunnels`：https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/
- `Setup`：https://developers.cloudflare.com/tunnel/setup/

### 第一步：下载 cloudflared

先下载 Windows 版 `cloudflared.exe`，放到项目根目录，或者放到系统环境变量可以找到的位置。

建议最终路径类似：

```text
E:\Grade_2_2\ai\hw4\cloudflared.exe
```

### 第二步：一键启动分享

仓库已经包含一个分享脚本：

```powershell
.\share.ps1
```

默认行为：

- 本地启动 `FastAPI` 服务
- 监听 `127.0.0.1:8010`
- 自动打开 `Cloudflare Tunnel`
- 在终端里打印一个 `trycloudflare.com` 的公网地址

如果你的 `cloudflared.exe` 不在项目根目录，可以手动指定：

```powershell
.\share.ps1 -CloudflaredPath "C:\你的路径\cloudflared.exe"
```

如果你想换端口，也可以这样：

```powershell
.\share.ps1 -Port 8000
```

### 第三步：把公网链接发给别人

脚本成功后，终端里会出现一个类似下面的地址：

```text
https://xxxx-xxxx.trycloudflare.com
```

你可以直接分享这些链接：

- 首页：`https://xxxx-xxxx.trycloudflare.com/`
- 应用场景：`https://xxxx-xxxx.trycloudflare.com/scenarios`
- API 展示台：`https://xxxx-xxxx.trycloudflare.com/studio`
- 报告中心：`https://xxxx-xxxx.trycloudflare.com/reports`
- API 文档：`https://xxxx-xxxx.trycloudflare.com/docs`

### 注意事项

- 你的电脑要保持开机。
- `share.ps1` 运行的终端不要关闭。
- 按 `Ctrl + C` 会停止隧道，并自动结束本地服务。
- `Quick Tunnel` 更适合演示和临时分享，不适合长期正式上线。

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

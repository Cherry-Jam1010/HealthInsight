# HealthInsight API 架构说明

## 读完 `FRAME.md` 之后，产品定位发生了什么变化

你的产品本质上不是“一个模型接口”，而是一个面向机构的健康数据洞察与决策支持平台。它对应的是一条完整链路：

1. 数据接入
2. 数据体检
3. 人群画像
4. 风险解释
5. 公平性检查
6. 阈值推荐
7. 定制化报告

但当前仓库只有人口学、体力活动和睡眠三类数据，没有 PHQ-9 结果变量，因此第一版 API 不应该硬做成“抑郁预测服务”，而应该老老实实定位成 **机构级健康洞察 API**。

## 成熟 API 的设计启发

### 1. 路径要稳定、清晰、资源化

像 Stripe 这类成熟 API 会坚持资源式 URL 和稳定语义。这对你的产品非常适合，因为用户最终会关心“我能拿到什么资源”，而不是你的内部脚本怎么跑。

当前推荐保留的结构：

- `/api/v1/datasets`
- `/api/v1/summary`
- `/api/v1/population-profile`
- `/api/v1/priority-cohorts`
- `/api/v1/reports/{audience}`

参考：

- https://docs.stripe.com/api

### 2. 从第一天开始就做版本化

你后面很可能还会加上传数据、公平性审计、阈值优化、PHQ-9 模块和 PDF 报告。如果现在不做版本化，后面会非常难维护。

`FastAPI` 很适合这里，因为它天然支持 OpenAPI 文档和交互式接口页。

参考：

- https://fastapi.tiangolo.com/features/
- https://fastapi.tiangolo.com/tutorial/metadata/

### 3. 站在医疗资源 API 的思路去组织能力

FHIR 这类医疗 API 的一个重要思路是：先明确“系统能提供哪些资源”，再明确“每种资源怎样被读取和解释”。

HealthInsight 不是 FHIR 服务器，但这个设计思想仍然值得借鉴，所以当前版本保留了 `/api/v1/capabilities` 这种“能力声明”接口。

参考：

- https://build.fhir.org/http.html

### 4. 提前为重任务接口留出扩展位

现在这版大多是只读展示型接口，所以 `GET` 足够。但等你后面做用户上传、自定义分析、公平性审计和报告导出时，建议升级成任务型资源：

- `POST /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`

这样比把所有逻辑都塞进同步接口里更像成熟产品。

参考：

- https://docs.cloud.google.com/healthcare-api/docs/api-structure
- https://cloud.google.com/healthcare-api/docs/how-tos/long-running-operations

## 当前推荐的产品化结构

### 第一阶段：真实可讲的 MVP

基于当前仓库，最合理的做法是先开放这些能力：

- 数据集目录
- 数据质量与覆盖率摘要
- 分组人群画像
- 行为负担优先级群体
- 面向不同角色的摘要报告

前端表达也要同步收束：

- 强调公共卫生与心理健康机构的“筛查支持”
- 强调这是“机构决策支持工具”
- 明确它“不是个人诊断服务”

### 第二阶段：接入真实心理健康标签

当你补上下面这些数据后，产品就能进入你最初设想的主线：

- `P_DPQ.xpt`：PHQ-9 抑郁量表
- BMI、慢病、医疗可及性等更多变量模块

这时就可以新增：

- `GET /api/v1/outcomes/phq9`
- `GET /api/v1/fairness/group-audit`
- `GET /api/v1/thresholds/recommendation`
- `GET /api/v1/reports/researcher?scenario=phq9-screening`

### 第三阶段：平台化与上传分析

如果你想把它做成真正像产品的平台，还可以再往下走：

- 支持用户上传 CSV / Excel
- 建立异步分析任务
- 缓存报告结果
- 导出 PDF / JSON / 证据包

## 为什么当前技术选型合适

`FastAPI` 非常适合这类课程项目向产品原型过渡的阶段，因为它能同时满足：

- 类型校验
- 版本化接口
- 自动生成 OpenAPI
- 可直接挂网页模板与静态资源

这意味着你可以用一个代码库，同时支撑：

- 后端 API
- 中文产品官网
- 在线展示台
- 角色化报告页

也就是说，它已经不只是“会跑的作业”，而是在向“可展示、可讲述、可继续扩展”的产品原型发展。

# HealthInsight API 快速开始

## 这份文档给谁用

- 如果你是产品用户：按“产品用户 3 步”走
- 如果你是开发者：按“开发者 4 步”走

## 产品用户 3 步

### 第 1 步：打开首页

先看平台能解决什么问题：

- 看 `PHQ-9 高风险率`
- 看 `双周期对照`
- 看 `重点人群`

### 第 2 步：打开在线演示

进入 `/studio`，重点看：

- `population-profile`
- `priority-cohorts`
- `cycle-comparison`
- `threshold-simulate`

### 第 3 步：打开报告中心

进入 `/reports`，按角色切换：

- 研究团队
- 管理团队
- 临床团队
- 技术团队

## 开发者 4 步

### 第 1 步：确认服务在线

```bash
GET /api/v1/health
```

### 第 2 步：先读取总体摘要

```bash
GET /api/v1/summary
```

这个接口会返回：

- 当前 PHQ-9 风险摘要
- 历史行为基线摘要
- 样本覆盖率
- 阈值参考

### 第 3 步：再读分组结果

```bash
GET /api/v1/population-profile?group_by=income_band
GET /api/v1/cycle-comparison?group_by=age_band
```

### 第 4 步：最后接入模拟和简报

```bash
GET /api/v1/threshold-simulate?threshold=10&weekly_capacity=20
GET /api/v1/reports/manager
```

## 推荐接入顺序

1. `health`
2. `summary`
3. `population-profile`
4. `cycle-comparison`
5. `risk-factors`
6. `threshold-simulate`
7. `reports/{audience}`

## 关键入口

- 站点首页：`/`
- 使用指南：`/guide`
- 在线演示：`/studio`
- 报告中心：`/reports`
- 接口文档：`/docs`
- OpenAPI：`/api/v1/openapi.json`

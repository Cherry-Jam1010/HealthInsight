# 无需信用卡的部署方案

如果 Render 要求绑定银行卡，而你现在没有卡，最适合这个项目的方案有两个：

## 方案一：Hugging Face Spaces

适合：

- 需要一个公开网址
- 不想绑卡
- 接受免费实例可能休眠

官方文档：

- Spaces 总览：https://huggingface.co/docs/hub/en/spaces-overview
- Docker Spaces：https://huggingface.co/docs/hub/main/spaces-sdks-docker

这个仓库已经补好了：

- `Dockerfile`
- `.dockerignore`

因此可以直接作为 Docker Space 部署。

### 操作步骤

1. 注册并登录 Hugging Face。
2. 打开 Spaces 页面：`https://huggingface.co/spaces`
3. 点击 `Create new Space`
4. 填写：
   - Owner：你的账号
   - Space name：例如 `healthinsight`
   - License：可选
   - Visibility：Public
   - SDK：`Docker`
5. 创建完成后，你会得到一个新的 Space 仓库。
6. 把当前 GitHub 仓库代码上传到这个 Space 仓库。
7. 等待自动构建完成。
8. 构建成功后，Hugging Face 会给你一个公开链接。

### 运行端口

Docker Space 默认对外暴露端口 `7860`。当前 `Dockerfile` 已经兼容。

## 方案二：Cloudflare Tunnel

适合：

- 想马上把网站发给老师或同学看
- 不需要真正长期托管
- 你自己的电脑可以保持开机

官方文档：

- https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/

### 操作步骤

1. 本地启动项目：

```powershell
.\start.ps1 -Port 8010
```

2. 安装并运行 `cloudflared`
3. 执行：

```powershell
cloudflared tunnel --url http://127.0.0.1:8010
```

4. 它会给你一个 `https://xxxx.trycloudflare.com` 链接。
5. 直接把这个链接发给别人即可。

## 两种方案怎么选

- 要“真正上线”：选 Hugging Face Spaces
- 要“今天就能分享”：选 Cloudflare Tunnel

# B站UP主动态监控系统

一个功能完整的B站UP主动态监控系统，支持获取多种动态类型，自动下载图片，通过多种渠道推送通知，并提供Web管理界面。

## 功能特性

- **动态获取**：支持图文、视频、专栏、转发、充电专属等多种动态类型
- **图片下载**：自动下载动态中的图片到本地
- **数据存储**：SQLite数据库持久化存储
- **定时监控**：可配置检查间隔，支持随机抖动防检测
- **多UP主支持**：同时监控多个UP主
- **Cookie认证**：支持Cookie访问授权内容，扫码登录自动刷新
- **WBI签名**：自动处理B站API的WBI签名校验
- **通知推送**：支持企业微信、钉钉、邮件、Telegram、PushPlus、Server酱等通知方式
- **Web管理**：提供Web管理界面，支持SSE实时推送
- **Docker部署**：支持Docker一键部署

## 安装

```bash
pip install .
```

## 快速开始

```bash
# 复制配置文件
cp config.example.yaml config.yaml

# 编辑配置文件，添加UP主和Cookie

# 运行监控
bili-monitor monitor

# 运行Web服务
bili-monitor web
```

Web 管理面板默认监听 `http://127.0.0.1:5000/`，也可以指定端口：

```bash
bili-monitor web --port 8000
```

在 Web 面板点击启动监控后，可以通过 `/api/status` 查看运行状态。

## 常见问题

### Cookie 显示过期但日志里有 WinError 10013

如果日志出现类似下面的错误：

```text
Cookie 已过期: HTTPSConnectionPool(host='api.bilibili.com', port=443)...
Failed to establish a new connection: [WinError 10013]
```

这通常不是 Cookie 被 B 站判定失效，而是当前 Python 进程没有权限访问外网套接字，导致访问 `api.bilibili.com` 失败后被程序记录为 Cookie 过期。处理方式：

1. 确认防火墙、安全软件或运行环境允许 Python 访问外网。
2. 在 Codex/受限沙箱中运行时，使用允许网络访问的方式启动 Web 服务。
3. 重新启动服务后，再从 Web 面板启动监控并观察日志；如果能看到 `Cookie 有效`、UP 主信息或动态列表日志，说明网络权限已恢复。

## Docker部署

```bash
docker-compose up -d
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
black src/ tests/

# 代码检查
ruff check src/ tests/
```

## 许可证

MIT License

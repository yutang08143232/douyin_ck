# 抖音续火花自动脚本

每天凌晨自动给抖音好友发私信，维持火花（连续聊天标识）。
带 Web 管理面板，可视化配置，操作简单。

## 功能特性

- **Web 管理面板**：可视化配置，无需改代码
- **多好友支持**：批量给多个好友发送消息
- **三级好友查找**：昵称 → sec_uid → user_id，逐级回退
- **消息API集成**：支持调用真实API获取消息，或使用内置随机消息（Mock模式）
- **失败重试**：发送失败自动重试，默认3次
- **Cookie自动续期**：每次运行尝试刷新Cookie，延长有效期
- **邮箱通知**：全部失败 / Cookie过期 / 每日简报 三种通知触发条件
- **日志记录**：完整的日志记录，支持按大小滚动
- **手动触发**：Web面板可一键立即发送

## 技术栈

- Python 3.8+
- Flask（Web 管理面板）
- Playwright（模拟浏览器操作，规避风控）
- YAML 配置
- SMTP 邮件通知
- Linux Crontab 定时任务

## 目录结构

```
douyin_ck/
├── main.py              # 主程序入口（定时任务调用）
├── config.yaml          # 配置文件（自动创建）
├── config.example.yaml  # 配置模板
├── requirements.txt     # Python 依赖
├── deploy.sh            # Linux 一键部署脚本
├── run.sh               # 运行入口（供 crontab 调用）
├── web.sh               # Web 面板管理脚本
├── README.md            # 说明文档
├── src/
│   ├── config_loader.py   # 配置加载
│   ├── message_provider.py # 消息提供者（API/Mock）
│   ├── douyin_sender.py   # 抖音私信发送核心
│   ├── cookie_manager.py  # Cookie 管理
│   ├── email_notifier.py  # 邮箱通知
│   └── logger_setup.py    # 日志配置
├── web/
│   ├── app.py             # Flask 后端
│   ├── templates/         # HTML 模板
│   └── static/            # 静态资源（CSS/JS）
├── logs/                # 日志目录（自动创建）
└── browser_data/        # 浏览器数据目录（自动创建）
```

## 快速开始

### 1. 部署（Linux）

```bash
# 上传项目到服务器
scp -r douyin_ck user@server:/path/to/

cd /path/to/douyin_ck
chmod +x deploy.sh
./deploy.sh
```

### 2. 启动 Web 管理面板（推荐）

```bash
./web.sh start    # 启动
./web.sh status   # 查看状态
./web.sh stop     # 停止
./web.sh restart  # 重启
```

访问 `http://服务器IP:5000`，默认账号密码：

- 用户名：`admin`
- 密码：`admin123`

> ⚠️ **请务必在 Web 面板中修改默认密码！**

### 3. Web 面板配置

登录后依次配置：

1. **Cookie设置**：粘贴抖音 Cookie
2. **好友管理**：添加要续火花的好友（填昵称即可）
3. **消息设置**：选择 Mock 模式或真实 API
4. **邮箱设置**：配置 163 邮箱（已默认配置好）
5. **仪表盘**：点击"立即发送消息"测试

### 4. 设置定时任务

配置测试通过后，设置每天凌晨1点自动执行：

```bash
crontab -e
```

添加一行：

```
0 1 * * * cd /path/to/douyin_ck && ./run.sh >> logs/cron.log 2>&1
```

## 配置说明

### 好友查找策略

脚本会按以下优先级查找好友：

1. **昵称匹配**：在会话列表中搜索好友昵称（最常用）
2. **sec_uid 匹配**：抖音用户的唯一标识
3. **user_id 匹配**：数字ID

### Cookie 获取方法

1. 浏览器打开 https://www.douyin.com/chat 并登录
2. 按 F12 打开开发者工具
3. 切换到 Network 标签，刷新页面
4. 点击任意一个请求，在 Request Headers 中找到 Cookie
5. 完整复制 Cookie 值，粘贴到 Web 面板

### 邮箱配置

已默认配置 163 邮箱，只需启用即可：

- SMTP服务器：`smtp.163.com`
- 端口：`465`
- 发件人：`yutang3416026891@163.com`

> 注意：使用的是邮箱**授权码**，不是登录密码。

### HTTPS 配置（可选）

生产环境建议启用 HTTPS。修改 `config.yaml` 中的 `web.https`：

```yaml
web:
  https:
    enabled: true
    cert_file: "/path/to/cert.pem"
    key_file: "/path/to/key.pem"
```

或者使用 Nginx 反向代理更方便。

## 常见问题

### Cookie 多久过期？

抖音 Web 端 Cookie 有效期约 7-15 天。脚本每次运行会尝试刷新 Cookie，
如果刷新失败会通过邮件通知，届时需要重新获取 Cookie 填入。

### 会被风控吗？

- 设置合理的好友间隔（建议 10 秒以上）
- 消息内容尽量多样化（使用 API 获取不同内容）
- 不要一次给太多好友发消息
- 模拟真实浏览器行为（已内置随机延迟）

### 如何查看日志？

- Web 面板 → 运行日志 页面实时查看
- 或直接查看日志文件：`logs/douyin_spark.log`

## License

MIT

# 抖音续火花自动脚本

每天自动给抖音好友发私信，维持火花（连续聊天标识）。支持文字消息和表情包图片发送，带 Web 管理面板，可视化配置。

## 在线版本

已部署在线版本，依托羽棠小屋全局系统，无需自建服务器即可使用：

- **用户面板**：https://yutangxiaowu.cn/douyin_ck/
- **项目文档**：https://yutangxiaowu.cn/doc/douyin_ck_about.html

在线版本特性：
- 全站统一账号体系（QQ / GitHub OAuth 登录）
- Cookie 采用 RSA-OAEP + AES-256-GCM 混合加密传输与存储
- 自动识别好友（权限申请制）
- 好友级个性化配置（单独消息 / 定时发送 / 专属表情包）
- 管理员后台审核与运维

## 功能特性

- **Web 管理面板**：可视化配置，无需改代码
- **多好友支持**：批量给多个好友发送消息
- **三级好友查找**：昵称 -> sec_uid -> user_id，逐级回退
- **表情包发送**：接入表情包 API，支持发送随机表情包图片
- **消息池机制**：支持 Mock 内置消息 / 外部 API / 表情包三种模式
- **失败重试**：发送失败自动重试，默认 3 次
- **Cookie 自动续期**：每次运行尝试刷新 Cookie，延长有效期
- **邮箱通知**：全部失败 / Cookie 过期 / 每日简报三种通知触发条件
- **日志记录**：完整的日志记录，支持按大小滚动
- **定时任务**：支持 Linux Crontab 定时执行

## 技术栈

- **Python 3.8+** - 后端核心
- **Flask** - Web 管理面板
- **Playwright** - 浏览器自动化（模拟人工操作，规避风控）
- **SMTP** - 邮件通知
- **Nginx + PM2** - 生产环境部署（在线版本）
- **Vue 3 + Naive UI** - 管理后台（在线版本）

## 目录结构

```
douyin_ck/
├── main.py              # 主程序入口（定时任务调用）
├── config.yaml          # 配置文件（自动创建，含敏感信息，勿提交）
├── config.example.yaml  # 配置模板（脱敏示例）
├── requirements.txt     # Python 依赖
├── deploy.sh            # Linux 一键部署脚本
├── run.sh               # 运行入口（供 crontab 调用）
├── web.sh               # Web 面板管理脚本
├── README.md
├── docs/
│   └── 抖音图片发送机制.md  # 图片发送技术文档
├── src/
│   ├── config_loader.py   # 配置加载与热更新
│   ├── message_provider.py # 消息提供者（Mock / Real API / Sticker）
│   ├── douyin_sender.py   # 抖音私信发送核心（文字 + 图片）
│   ├── cookie_manager.py  # Cookie 生命周期管理
│   ├── email_notifier.py  # SMTP 邮件通知
│   └── logger_setup.py    # 日志配置
├── web/
│   ├── app.py             # Flask 后端 API
│   ├── templates/         # HTML 模板
│   └── static/            # 静态资源（CSS/JS）
├── logs/                # 日志目录（自动创建）
└── browser_data/        # 浏览器数据目录（自动创建）
```

## 快速开始

### 方式一：使用在线版本（推荐）

直接访问 https://yutangxiaowu.cn/douyin_ck/ ，注册登录后即可使用，无需自建服务器。

### 方式二：自建部署（Linux）

#### 1. 部署

```bash
# 上传项目到服务器
scp -r douyin_ck user@server:/path/to/

cd /path/to/douyin_ck
chmod +x deploy.sh
./deploy.sh
```

#### 2. 启动 Web 管理面板

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

#### 3. Web 面板配置

登录后依次配置：

1. **Cookie 设置**：粘贴抖音 Cookie
2. **好友管理**：添加要续火花的好友（填昵称即可）
3. **消息设置**：选择 Mock 模式 / 真实 API / 表情包模式
4. **邮箱设置**：配置 SMTP 邮箱通知
5. **仪表盘**：点击"立即发送消息"测试

#### 4. 设置定时任务

配置测试通过后，设置每天凌晨 1 点自动执行：

```bash
crontab -e
```

添加一行：

```
0 1 * * * cd /path/to/douyin_ck && ./run.sh >> logs/cron.log 2>&1
```

## 配置说明

### 消息模式

| 模式 | 说明 | 配置项 |
|------|------|--------|
| `mock` | 内置随机消息池 | `message_api.mock.messages` |
| `real` | 外部 API 获取消息 | `message_api.real.url` |
| `sticker` | 发送表情包图片 | `message_api.sticker.url` |

### 好友查找策略

脚本会按以下优先级查找好友：

1. **昵称匹配**：在会话列表中搜索好友昵称（最常用）
2. **sec_uid 匹配**：抖音用户的唯一标识
3. **user_id 匹配**：数字 ID

### Cookie 获取方法

1. 浏览器打开 https://www.douyin.com/ 并登录
2. 按 F12 打开开发者工具
3. 切换到 Network 标签，刷新页面
4. 点击任意请求，在 Request Headers 中找到 Cookie
5. 完整复制 Cookie 值，粘贴到 Web 面板

> ⚠️ **Cookie 等同于登录凭证**，请勿泄露给他人。怀疑泄露时请立即退出抖音并修改密码。

### 邮箱配置

支持 163 邮箱或其他 SMTP 服务，配置 `config.yaml` 中的 `email` 部分：

```yaml
email:
  enabled: true
  smtp_server: "smtp.163.com"
  smtp_port: 465
  use_ssl: true
  sender: "your-email@163.com"
  password: "your-auth-code"  # 授权码，不是登录密码
  receivers:
    - "your-email@163.com"
```

### HTTPS 配置（可选）

生产环境建议启用 HTTPS。修改 `config.yaml` 中的 `web.https`：

```yaml
web:
  https:
    enabled: true
    cert_file: "/path/to/cert.pem"
    key_file: "/path/to/key.pem"
```

或者使用 Nginx 反向代理。

## 常见问题

### Cookie 多久过期？

抖音 Web 端 Cookie 有效期约 7-15 天。脚本每次运行会尝试刷新 Cookie，如果刷新失败会通过邮件通知，届时需要重新获取 Cookie 填入。

### 会被风控吗？

- 设置合理的好友间隔（建议 10 秒以上）
- 消息内容尽量多样化（使用 API 或表情包模式）
- 不要一次给太多好友发消息
- 模拟真实浏览器行为（已内置随机延迟）

### 如何查看日志？

- Web 面板运行日志页面实时查看
- 或直接查看日志文件：`logs/douyin_spark.log`

### 表情包图片如何发送？

图片发送通过 Playwright 模拟浏览器操作完成，核心流程：
1. 点击上传图标 -> 文件选择器选图 -> 弹出确认对话框 -> 点击"发送"按钮

详细技术文档见 [docs/抖音图片发送机制.md](docs/抖音图片发送机制.md)。

## 相关链接

- **在线版本**：https://yutangxiaowu.cn/douyin_ck/
- **项目文档**：https://yutangxiaowu.cn/doc/douyin_ck_about.html
- **表情包 API**：https://api.yutangxiaowu.cn/api/gif/random

## License

MIT

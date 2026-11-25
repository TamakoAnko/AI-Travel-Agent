# 本地启动指南

本项目由四个进程组成：**Redis → Milvus → 后端（FastAPI）→ 前端（Vue）**。
Redis 和 Milvus 跑在 WSL2 Ubuntu 里，后端和前端跑在 Windows 上。

## 0. 前置条件

| 依赖 | 位置 | 说明 |
|---|---|---|
| WSL2 + Ubuntu | Windows | 提供 Linux 环境，Redis / Milvus 都装在里面 |
| Redis | WSL | `127.0.0.1:6379`，密码 `123456` |
| Milvus | WSL | `milvus-server`（pip 安装），gRPC 端口 19530 |
| Python 3.11 + uv | Windows | 后端依赖与运行 |
| Node 20 + npm | Windows | 前端依赖与运行 |

`.env` 里与启动相关的配置：

```env
RAG_BACKEND=milvus                  # milvus | sqlite
MILVUS_URI=http://<WSL-IP>:19530    # WSL 重启后会变
REDIS_PASSWORD=123456
```

## 1. 手动启动（四个终端）

### 1.1 Redis（WSL）

```bash
sudo service redis-server start
redis-cli -a 123456 ping      # 返回 PONG 即成功
```

### 1.2 Milvus（WSL，前台常驻，窗口不要关）

```bash
~/milvus-venv/bin/milvus-server --data ~/milvus-data
```

验证（另开一个 WSL 标签）：

```bash
curl -sf http://localhost:9091/healthz && echo MILVUS_OK
```

### 1.3 取 WSL 的 IP，写进 .env

```powershell
wsl -d Ubuntu -- ip -4 addr show eth0
```

把输出里的 `inet 172.x.x.x` 填到 `.env`：

```env
MILVUS_URI=http://172.x.x.x:19530
```

### 1.4 后端（Windows PowerShell）

```powershell
cd C:\Users\xzj12\Desktop\agent\AI-Travel-Agent
$env:UV_CACHE_DIR="$PWD\.uv-cache"
uv run uvicorn ai_travel_agent.api:app --port 8000
```

看到 `Uvicorn running on http://127.0.0.1:8000` 即成功。

### 1.5 前端（另一个 PowerShell）

```powershell
cd C:\Users\xzj12\Desktop\agent\AI-Travel-Agent\frontend
npm run dev
```

浏览器打开 <http://localhost:3000>。

## 2. 一键启动

脚本位置：`scripts/dev_up.ps1`

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev_up.ps1
```

它做四件事：

1. 读取 WSL 的 IP
2. 把 `.env` 里的 `MILVUS_URI` 更新成当前 IP
3. 启动 WSL 里的 Redis
4. 后台启动 `milvus-server`（日志写到 `~/milvus.log`）

脚本**不包含**后端和前端，启动依赖后照常执行 1.4 / 1.5。

## 3. 验证

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

期望（关键字段）：

```json
{
  "status": "healthy",
  "services": {
    "deepseek": true,
    "redis": true,
    "rag": true,
    "rag_backend": "milvus",
    "embedding": "text-embedding-v3"
  }
}
```

- `rag_backend` 是 `milvus`：正常走 Milvus
- 是 `sqlite`：Milvus 没连上，已自动回退（功能可用，检索走 SQLite）

## 4. 停止

```powershell
# 后端 / 前端：各自窗口 Ctrl+C
wsl --shutdown        # 一次性停掉 Redis 和 Milvus
```

## 5. 常用维护命令

```powershell
# 重建知识库索引（会清空并重新写入 Milvus 集合）
uv run ai-travel-agent ingest --reset

# 检索评测（向量 vs 混合）
uv run python scripts/eval_rag.py --compare

# 全量测试
uv run pytest -q
```

## 6. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 后端报 `WinError 10013` | 8000 落在 Windows 保留端口段（7947-8046） | 管理员 PowerShell：`net stop winnat` → `netsh int ipv4 add excludedportrange protocol=tcp startport=8000 numberofports=1` → `net start winnat` |
| 报 `NOAUTH Authentication required` | Redis 要密码但 `.env` 没配 | `.env` 写 `REDIS_PASSWORD=123456` |
| `rag_backend` 显示 `sqlite` | Milvus 没启动或 `MILVUS_URI` 的 IP 过期 | 重跑 `scripts/dev_up.ps1`，或重新取 IP 改 `.env` 后重启后端 |
| 前端地图空白 | 百度 AK 白名单/SDK 问题 | 打开控制台看 `BMapGL` 报错 |

## 7. 为什么 Milvus 要放在 WSL

`milvus-lite` 的 Windows wheel 不完整，Windows 原生跑不起来；WSL2 是官方支持的 Linux 环境，且 Windows 能通过 WSL 的 IP 访问 19530。

如果换成 Docker 部署 Milvus standalone，逻辑一样：把 `MILVUS_URI` 指向容器映射出来的地址即可，代码不用改。
